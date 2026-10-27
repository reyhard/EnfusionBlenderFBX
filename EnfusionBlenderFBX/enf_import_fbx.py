"""FBX import bridge and collection sorting for Enfusion FBX Tools.

EBT owns its importer and its per-asset collection sorter.  This add-on only
chooses between it and Blender's native importer; it deliberately does not
modify EBT.  When EBT is not available the local sorter reproduces the legacy
Enfusion grouping (LODs, colliders per usage, memory points, ...) from object
names, so a plain Blender FBX import ends up in the same Outliner layout.
"""

import os
import re

import bpy
from bpy.props import StringProperty
from bpy.types import Operator, Panel
from bpy_extras.io_utils import ImportHelper


_LOD_SUFFIX = re.compile(r"(?:_|\s)LOD(\d+)$", re.IGNORECASE)
_LOD_GROUP = re.compile(r"^LOD(\d+)$", re.IGNORECASE)
_LOD_COLLECTION = re.compile(r"(?:^|[_\s])LOD(\d+)$", re.IGNORECASE)

# Enfusion naming rules, mirrored from EBT so the local sorter works without
# EBT being loaded.  Prefix matching is case-insensitive.
_COLLIDER_PREFIXES = ("UBX", "USP", "UCX", "UCS", "UCL", "UTM")
_PROBE_VOLUME_PREFIXES = ("BOXVOL", "SPHVOL")
_LIGHT_PORTAL_PREFIXES = ("PRTVOL", "PRT", "BSP", "VL")
_MEMORY_POINT_PREFIXES = ("LC_", "COM_", "SOCKET_")

_GROUP_ORDER = (
    "Colliders",
    "Memory Points",
    "Skeletons",
    "Occluders",
    "Probe Volumes",
    "Light Portals",
)

# Marks collections owned by this sorter so re-sorting can clean them up
# without touching collections the user created manually.
_GROUP_PROPERTY = "enfusion_fbx_group"

# Single collection holding the sorted groups, matching what the panel has
# always produced for explicit sorting.
_SORT_ROOT_NAME = "Enfusion FBX Sorted"


def _preference(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def _starts_with(name, prefixes):
    upper = name.upper()
    return any(upper.startswith(prefix) for prefix in prefixes)


def _group_path(obj):
    """Return the collection path an object belongs to.

    The rules mirror EBT's Enfusion naming conventions so that colliders,
    memory points and other helper geometry are grouped even when the object
    carries no Enfusion custom properties.
    """
    name = obj.name

    if _starts_with(name, _COLLIDER_PREFIXES):
        usage = obj.get("usage")
        return ("Colliders", str(usage) if usage else "Empty")
    if _starts_with(name, _PROBE_VOLUME_PREFIXES):
        return ("Probe Volumes",)
    if name.upper().startswith("OCC"):
        return ("Occluders",)
    if _starts_with(name, _LIGHT_PORTAL_PREFIXES):
        return ("Light Portals",)
    if _starts_with(name, _MEMORY_POINT_PREFIXES):
        return ("Memory Points",)

    match = _LOD_SUFFIX.search(name)
    if match:
        return (f"LOD{int(match.group(1))}",)

    if obj.type == 'ARMATURE':
        return ("Skeletons",)
    if isinstance(obj.data, bpy.types.Mesh):
        # A mesh without an Enfusion suffix is treated as implicit LOD0.
        return ("LOD0",)
    return ("Other",)


def _new_group(parent, name, cache):
    key = (parent.name, name)
    collection = cache.get(key)
    if collection is not None:
        return collection

    collection = parent.children.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        collection[_GROUP_PROPERTY] = True
        parent.children.link(collection)
    cache[key] = collection
    return collection


def _target_collection(root, path, cache):
    parent = root
    for name in path:
        parent = _new_group(parent, name, cache)
    return parent


def _is_managed(collection):
    """True for collections this sorter owns or has named like its groups."""
    if collection.get(_GROUP_PROPERTY, False):
        return True
    name = collection.name
    return name in _GROUP_ORDER or name == "Other" or _LOD_GROUP.match(name) is not None


def _group_sort_key(collection):
    name = collection.name
    match = _LOD_GROUP.match(name)
    if match:
        return (1, int(match.group(1)), "")
    if name in _GROUP_ORDER:
        return (0, _GROUP_ORDER.index(name), "")
    if name == "Other":
        return (3, 0, "")
    return (2, 0, name.lower())


def _reorder_managed_children(collection):
    managed = [child for child in collection.children if _is_managed(child)]
    for child in sorted(managed, key=_group_sort_key):
        collection.children.unlink(child)
        collection.children.link(child)
        _reorder_managed_children(child)


def _prune_empty_groups(collection):
    for child in list(collection.children):
        _prune_empty_groups(child)
        if not _is_managed(child):
            continue
        if child.objects or child.children:
            continue
        collection.children.unlink(child)
        if child.users == 0:
            bpy.data.collections.remove(child)


def _sort_root(scene):
    """Return the collection that holds the sorted groups, creating it once."""
    root = scene.collection.children.get(_SORT_ROOT_NAME)
    if root is None:
        root = bpy.data.collections.get(_SORT_ROOT_NAME)
        if root is None:
            root = bpy.data.collections.new(_SORT_ROOT_NAME)
        if root.name not in scene.collection.children:
            scene.collection.children.link(root)
    return root


def _sort_objects(objects, root):
    """Move objects into Enfusion groups directly under ``root``.

    Objects are unlinked from every other collection, the same way the legacy
    EBT sorter moved them, so the Outliner no longer shows duplicate rows in
    the scene collection.
    """
    objects = [obj for obj in objects if obj is not None and obj.name in bpy.data.objects]
    if not objects:
        return root

    cache = {}
    targets = {}
    for obj in objects:
        target = _target_collection(root, _group_path(obj), cache)
        targets.setdefault(target, []).append(obj)

    for target, grouped_objects in targets.items():
        for obj in grouped_objects:
            for collection in list(obj.users_collection):
                if collection is not target:
                    collection.objects.unlink(obj)
            if target not in obj.users_collection:
                target.objects.link(obj)

    _prune_empty_groups(root)
    _reorder_managed_children(root)
    return root


def _lowest_lod_objects(scene):
    """One object per lowest LOD collection, used to expand them after folding."""
    lod_collections = []
    for collection in scene.collection.children_recursive:
        match = _LOD_COLLECTION.search(collection.name)
        if match:
            lod_collections.append((int(match.group(1)), collection))

    if not lod_collections:
        return []

    lowest = min(index for index, _ in lod_collections)
    objects = []
    for index, collection in lod_collections:
        if index != lowest:
            continue
        first_object = next(iter(collection.objects), None)
        if first_object is not None:
            objects.append(first_object)
    return objects


def _fold_outliners(context):
    """Collapse the Outliner, then expand the lowest LOD again."""
    screen = getattr(context, "screen", None)
    if screen is None:
        return False

    if not any(area.type == 'OUTLINER' for area in screen.areas):
        return False

    window = getattr(context, "window", None)
    scene = getattr(context, "scene", None)

    def apply_outliner_state():
        if window is None or window.screen is None:
            return None
        outliners = [area for area in window.screen.areas if area.type == 'OUTLINER']
        if not outliners:
            return None

        visible_objects = _lowest_lod_objects(scene)

        view_layer = window.view_layer
        previous_active = view_layer.objects.active
        try:
            for area in outliners:
                region = next((item for item in area.regions if item.type == 'WINDOW'), None)
                if region is None:
                    continue
                try:
                    with bpy.context.temp_override(window=window, area=area, region=region):
                        for _ in range(32):
                            bpy.ops.outliner.show_one_level(open=False)
                        for obj in visible_objects:
                            if obj.name in view_layer.objects:
                                view_layer.objects.active = obj
                                bpy.ops.outliner.show_active()
                except RuntimeError as error:
                    print(f"Enfusion FBX Tools: could not set Outliner state: {error}")
        finally:
            view_layer.objects.active = previous_active
        return None

    # EBT may have just created nested collections; a timer lets the Outliner
    # rebuild its tree before invoking operators that act on visible rows.
    bpy.app.timers.register(apply_outliner_state, first_interval=0.2)
    return True


def _require_ebt_workbench():
    from EnfusionBlenderTools.ebt.ebt_utils import raise_if_wb_is_not_ready

    raise_if_wb_is_not_ready()


def _import_with_ebt(filepath):
    _require_ebt_workbench()
    result = bpy.ops.view3d.ebt_import_fbx(filepath=filepath, sort_into_collections=True)
    if 'FINISHED' not in result:
        raise RuntimeError(f"EBT FBX import did not finish: {result}")


def _import_with_blender(filepath):
    before = set(bpy.data.objects)
    result = bpy.ops.wm.fbx_import(filepath=filepath)
    if 'FINISHED' not in result:
        raise RuntimeError(f"Blender FBX import did not finish: {result}")
    scene = bpy.context.scene
    _sort_objects(set(bpy.data.objects) - before, _sort_root(scene))


class EnfusionFBXTools_ImportFBX(Operator, ImportHelper):
    bl_idname = "importenfusion.fbx"
    bl_label = "Import FBX"
    bl_description = "Import through EBT when available, or Blender's native FBX importer"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx", options={'HIDDEN'})

    def execute(self, context):
        mode = getattr(_preference(context), "import_mode", 'AUTOMATIC')
        try:
            if mode == 'BLENDER':
                _import_with_blender(self.filepath)
            elif mode == 'EBT':
                _import_with_ebt(self.filepath)
            else:
                try:
                    _require_ebt_workbench()
                except Exception as error:
                    print(f"Enfusion FBX Tools: EBT unavailable ({error}); using native FBX import.")
                    _import_with_blender(self.filepath)
                else:
                    _import_with_ebt(self.filepath)
        except Exception as error:
            self.report({'ERROR'}, f"FBX import failed: {error}")
            return {'CANCELLED'}

        _fold_outliners(context)
        bpy.context.scene['enfusion_filepath'] = self.filepath
        if hasattr(bpy.context.scene, "ebt_xob_path"):
            bpy.context.scene.ebt_xob_path = self.filepath.lower().replace(".fbx", ".xob")
        return {'FINISHED'}


class EnfusionFBXTools_FoldCollections(Operator):
    bl_idname = "enfusionfbx.fold_collections"
    bl_label = "Fold"
    bl_description = "Collapse collection trees in all visible Outliner editors, leaving the lowest LOD expanded"

    def execute(self, context):
        if not _fold_outliners(context):
            self.report({'INFO'}, "No Outliner available to fold")
        return {'FINISHED'}


class EnfusionFBXTools_SortCollections(Operator):
    bl_idname = "enfusionfbx.sort_collections"
    bl_label = "Sort"
    bl_description = "Sort every object in the scene into LOD, collider and helper collections, then fold"

    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _sort_objects(list(context.scene.objects), _sort_root(context.scene))
        if not _fold_outliners(context):
            self.report({'INFO'}, "Collections sorted; no Outliner available to fold")
        return {'FINISHED'}


class EnfusionFBXTools_ImportPanel(Panel):
    bl_label = "Enfusion FBX"
    bl_idname = "VIEW3D_PT_enfusion_fbx_import"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Enfusion"

    def draw(self, _context):
        layout = self.layout
        layout.operator(EnfusionFBXTools_ImportFBX.bl_idname, icon='IMPORT')
        layout.label(text="Collections")
        row = layout.row(align=True)
        row.operator(EnfusionFBXTools_SortCollections.bl_idname, icon='SORTALPHA')
        row.operator(EnfusionFBXTools_FoldCollections.bl_idname, icon='TRIA_DOWN')
