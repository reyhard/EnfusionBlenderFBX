import bpy
from bpy.types import Operator

class EnfusionFBXTools_ExportFBX(Operator):
    """Script to export existing file to Workbench"""      # Use this as a tooltip for menu items and buttons.
    bl_idname = "exportenfusion.object"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Export to FBX"         # Display name in the interface.
    bl_options = {'REGISTER'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        exportPath = ""

        # Show pop up window if FBX file path is missing
        try:
            exportPath = bpy.context.scene['enfusion_filepath']
        except:
            msg = 'Quick export function needs path to existing FBX file!'
            bpy.ops.exportenfusion.message('INVOKE_DEFAULT', message = msg) 
            return {'CANCELLED'} 
        
        try:
            betterFBX = bpy.context.preferences.addons["EnfusionBlenderFBX"].preferences.export_better_fbx
        except:
            betterFBX = False

        if(betterFBX):
            print("Using Better FBX addon for export")
            bpy.ops.better_export.fbx(
                filepath=exportPath,
                my_fbx_version='FBX201400',
                use_animation=False,
                my_scale=100/(bpy.context.preferences.addons["EnfusionBlenderFBX"].preferences.scalefactor),
                use_optimize_for_game_engine=False,
                use_ignore_armature_node=True)
            return {'FINISHED'} 

        # The original script
        bpy.ops.export_scene.fbx(
            filepath=exportPath,
            check_existing=False,
            object_types={ 'MESH', 'OTHER', 'EMPTY', 'ARMATURE'},
            use_custom_props=True,
            bake_anim=False,
            add_leaf_bones=False,
            global_scale=1/(bpy.context.preferences.addons["EnfusionBlenderFBX"].preferences.scalefactor),
            use_selection=False,
            use_active_collection=False)

        return {'FINISHED'}            # Lets Blender know the operator finished successfully


class ExportEnfusionMessageBox(bpy.types.Operator):
    bl_idname = "exportenfusion.message"
    bl_label = ""
 
    message : bpy.props.StringProperty(
        name = "message",
        description = "message",
        default = ''
    )

    def execute(self, context):
        self.report({'INFO'}, self.message)
        return {'FINISHED'} 
 
    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=300)
 
    def draw(self, context):
        layout = self.layout
        layout.label(text = self.message)
        layout.operator("exportenfusion.select", text="Select FBX to overwrite")
 
class ExportEnfusionSelectFile(bpy.types.Operator):
    bl_idname = "exportenfusion.select"
    bl_label = "Select FBX file"

    filter_glob : bpy.props.StringProperty(
        default="*.fbx",
        options={'HIDDEN'})

    filepath : bpy.props.StringProperty(subtype="FILE_PATH") 

    def execute(self, context):
        bpy.context.scene['enfusion_filepath'] = self.filepath
        bpy.ops.exportenfusion.object()

        return {'FINISHED'}

    def invoke(self, context, event): # See comments at end  [1]
        context.window_manager.fileselect_add(self) 

        return {'RUNNING_MODAL'}  