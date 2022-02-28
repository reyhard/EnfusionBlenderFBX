import os
from sys import argv
import bpy
import addon_utils

print("new script launched")

try:
    argv = argv[argv.index("--") + 1:]

    scalefactor = 1

    # get all installed addons (non active too)
    addons_list_modules = {}
    addon_utils.modules(module_cache=addons_list_modules, refresh=True)
    bpy.ops.preferences.addon_refresh()

    # automatically enable enfusion tools
    if "EnfusionFBXTools" in addons_list_modules:
        if not ( "EnfusionTools" in bpy.context.preferences.addons.keys() ) :
            bpy.ops.preferences.addon_enable(module='EnfusionTools')
        # import scale factor
        scalefactor = bpy.context.preferences.addons["workbench_export_fbx"].preferences.scalefactor
    
    # format specific options... change as you like
    args_fbx = dict(
        global_scale=scalefactor,
        )

    args_obj = dict(
        # use_image_search=False,
        )

    args_3ds = dict(
        # constrain_size=0.0,
        )

    for f in argv:
        ext = os.path.splitext(f)[1].lower()
        if ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=f, **args_fbx)
            bpy.context.scene['enfusion_filepath'] = f
        elif ext == ".obj":
            bpy.ops.import_scene.obj(filepath=f, **args_obj)
        elif ext == ".3ds":
            bpy.ops.import_scene.autodesk_3ds(filepath=f, **args_3ds)
        else:
            print("Extension %r is not known!" % ext)


    bpy.ops.view3d.enf_objectname()
    bpy.ops.view3d.sort()
    bpy.ops.physmat.validate()
except:
    argv = ""