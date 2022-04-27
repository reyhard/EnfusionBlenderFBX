import os
from sys import argv
import bpy
import addon_utils

try:
    argv = argv[argv.index("--") + 1:]
    print("new script launched")

    scalefactor = 1

    # get all installed addons (non active too)
    addons_list_modules = {}
    addon_utils.modules(module_cache=addons_list_modules, refresh=True)
    bpy.ops.preferences.addon_refresh()

    # automatically enable enfusion tools
    if "EnfusionBlenderFBX2" in addons_list_modules:
        if not ( "EnfusionBlenderFBX" in bpy.context.preferences.addons.keys() ) :
            bpy.ops.preferences.addon_enable(module='EnfusionBlenderFBX')
        # import scale factor
        scalefactor = bpy.context.preferences.addons["workbench_export_fbx"].preferences.scalefactor
    
    # format specific options... change as you like
    args_fbx = dict(
        global_scale=scalefactor,
        )

    for f in argv:
        ext = os.path.splitext(f)[1].lower()
        if ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=f, **args_fbx)
            bpy.context.scene['enfusion_filepath'] = f
            bpy.context.scene.xob_meta_path = f.lower().replace("fbx","xob") + ".meta"
        else:
            print("Extension %r is not known!" % ext)


    bpy.ops.view3d.ebt_sort()
except:
    argv = ""