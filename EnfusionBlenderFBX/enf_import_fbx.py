import os
from sys import argv
import bpy
import addon_utils

try:
    argv = argv[argv.index("--") + 1:]
    print("new script launched")

    scalefactor = 1

    # format specific options... change as you like
    args_fbx = dict(
        global_scale=scalefactor,
        )


    def deferred_sort():
        if hasattr(bpy.context, 'view_layer'):
            for f in argv:
                ext = os.path.splitext(f)[1].lower()
                if ext == ".fbx":
                    #bpy.ops.import_scene.fbx(filepath=f, **args_fbx)
                    bpy.context.scene['enfusion_filepath'] = f
                    bpy.context.scene.ebt_xob_path = f.lower().replace("fbx","xob") #+ ".meta"
                else:
                    print("Extension %r is not known!" % ext)
            bpy.ops.ebt.sort_collections(fold_collections=True, hide_collections=True,
                                        separate_by_material=False, fix_lod_postfix=False)
            return None  # Stop the timer
        return 0.1  # Check again in 0.1 seconds

    # Register timer instead of direct call
    bpy.app.timers.register(deferred_sort)

except (AttributeError, TypeError, ValueError) as e:
    print(f"Error processing argv: {e}")
    argv = ""