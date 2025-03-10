bl_info = {
    "name": "Batch STL Exporter",
    "blender": (4, 0, 0),  # Adjust this if needed for other versions
    "category": "Import-Export",
    "author": "Your Name",
    "version": (1, 0, 0),
    "location": "File > Export > Batch STL Exporter",
    "description": "Exports all visible mesh objects as individual STL files",
    "warning": "",
    "wiki_url": "",
    "support": "COMMUNITY"
}

import bpy
import os

class OBJECT_OT_batch_export_stl(bpy.types.Operator):
    """Export all visible mesh objects as separate STL files"""
    bl_idname = "export_mesh.batch_stl"
    bl_label = "Export Visible Objects as STL"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Set output directory (relative to .blend file location)
        output_dir = bpy.path.abspath("//exported_stls/")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.visible_get():  # Skip hidden objects
                # Deselect everything and select the object
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                # Store original state of array modifiers and disable them temporarily
                original_array_states = {}
                for mod in obj.modifiers:
                    if mod.type == 'ARRAY':
                        original_array_states[mod.name] = mod.show_viewport
                        mod.show_viewport = False  # Disable for export

                # Create filename and complete file path
                filename = f"{obj.name}.stl"
                filepath = os.path.join(output_dir, filename)

                # Export the object
                bpy.ops.wm.stl_export(
                    filepath=filepath,
                    export_selected_objects=True,
                    ascii_format=False,
                    apply_modifiers=True,
                    global_scale=1.0,
                    use_scene_unit=True,
                    forward_axis='Y',
                    up_axis='Z'
                )
                self.report({'INFO'}, f"Exported: {filename}")

                # Restore original array modifier state
                for mod in obj.modifiers:
                    if mod.type == 'ARRAY' and mod.name in original_array_states:
                        mod.show_viewport = original_array_states[mod.name]

        self.report({'INFO'}, "Batch STL Export Complete!")
        return {'FINISHED'}

# Add to File > Export menu
def menu_func_export(self, context):
    self.layout.operator(OBJECT_OT_batch_export_stl.bl_idname, text="Batch STL Exporter")

# Register and unregister functions
def register():
    bpy.utils.register_class(OBJECT_OT_batch_export_stl)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_batch_export_stl)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
    register()
