import bpy
import configparser
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty, EnumProperty

from .enf_export_fbx import EnfusionFBXTools_ExportFBX 

# this is an internal API at the moment
import rna_keymap_ui
# store keymaps here to access after registration
addon_keymaps = []


def _matching_keymaps():
    """Yield this add-on's quick-export shortcuts from Blender's add-on map."""
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if not keyconfig:
        return
    for keymap in keyconfig.keymaps:
        for keymap_item in keymap.keymap_items:
            if (
                keymap_item.idname == EnfusionFBXTools_ExportFBX.bl_idname
                and keymap_item.type == 'S'
                and keymap_item.value == 'PRESS'
                and keymap_item.ctrl
                and keymap_item.shift
            ):
                yield keymap, keymap_item


def _ensure_keymap():
    existing = list(_matching_keymaps())
    if existing:
        addon_keymaps[:] = existing
        return

    wm = bpy.context.window_manager
    keyconfig = wm.keyconfigs.addon
    if keyconfig:
        keymap = keyconfig.keymaps.new(name='Window', space_type='EMPTY')
        keymap_item = keymap.keymap_items.new(
            EnfusionFBXTools_ExportFBX.bl_idname, 'S', 'PRESS', ctrl=True, shift=True
        )
        addon_keymaps[:] = [(keymap, keymap_item)]

class EnfusionToolsPreferences(AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package..
    bl_idname = __package__
    #bl_idname = "enfusionfbxtools.preferences"
    bl_label = "Enfusion FBX Tools preferences"         # Display name in the interface.
    bl_options = {'REGISTER'}  # Enable undo for the operator.

    scalefactor: IntProperty(
            name="Scale",
            default=1,
            )
    export_better_fbx: BoolProperty(
            name="Use Better FBX",
            default=False,
            )
    import_mode: EnumProperty(
            name="FBX Importer",
            description="Automatic uses EBT when Workbench is ready, otherwise Blender's native FBX importer",
            items=[
                ('AUTOMATIC', "Automatic", "Use EBT when Workbench is ready; otherwise native Blender import"),
                ('EBT', "EBT only", "Require Enfusion Blender Tools and a ready Workbench"),
                ('BLENDER', "Blender only", "Always use Blender's native FBX importer and local sorting"),
            ],
            default='AUTOMATIC',
            )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Import/Export settings")
        row = layout.row()
        layout.prop(self, "scalefactor")
        layout.prop(self, "export_better_fbx")
        layout.prop(self, "import_mode")

        layout.label(text="Keybinding")
        col = layout.column()
        kc = bpy.context.window_manager.keyconfigs.addon
        for km, kmi in addon_keymaps:
            km = km.active()
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

        # Add options if keymap is empty
        if addon_keymaps == []:
            _ensure_keymap()
                
    @classmethod
    def register(cls):
        _ensure_keymap()


def unregister():
    """Remove add-on keymaps so reloads do not leave duplicate shortcuts."""
    for km, kmi in list(_matching_keymaps()):
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError, ValueError):
            pass
    addon_keymaps.clear()

def save_settings(name, property):
    config = configparser.ConfigParser()
    config.read(__file__[:-18] + "\\settings.ini")
    config['DEFAULT'][name] = property
    with open(__file__[:-18] + "\\settings.ini", 'w') as configfile:
        config.write(configfile)

def load_settings(name):
    config = configparser.ConfigParser()
    try:
        config.read(__file__[:-18] + "\\settings.ini")
        return config['DEFAULT'][name]
    except:
        return ""
