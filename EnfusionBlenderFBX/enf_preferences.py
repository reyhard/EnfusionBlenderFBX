import bpy
import configparser
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty

from .enf_export_fbx import EnfusionFBXTools_ExportFBX 

# this is an internal API at the moment
import rna_keymap_ui
# store keymaps here to access after registration
addon_keymaps = []

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

    def draw(self, context):
        layout = self.layout
        layout.label(text="Import/Export settings")
        row = layout.row()
        layout.prop(self, "scalefactor")
        layout.prop(self, "export_better_fbx")

        layout.label(text="Keybinding")
        col = layout.column()
        kc = bpy.context.window_manager.keyconfigs.addon
        for km, kmi in addon_keymaps:
            km = km.active()
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)

        # Add options if keymap is empty
        if addon_keymaps == []:
            wm = bpy.context.window_manager
            kc = wm.keyconfigs.addon
            if kc:
                km = wm.keyconfigs.addon.keymaps.new(name='Window', space_type='EMPTY')
                kmi = km.keymap_items.new(EnfusionFBXTools_ExportFBX.bl_idname, 'S', 'PRESS', ctrl=True, shift=True)
                addon_keymaps.append((km, kmi))
                
    @classmethod
    def register(cls):
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if kc:
            km = wm.keyconfigs.addon.keymaps.new(name='Window', space_type='EMPTY')
            kmi = km.keymap_items.new(EnfusionFBXTools_ExportFBX.bl_idname, 'S', 'PRESS', ctrl=True, shift=True)
            addon_keymaps.append((km, kmi))

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
