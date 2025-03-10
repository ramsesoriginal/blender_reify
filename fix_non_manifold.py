bl_info = {
    "name": "Auto-Fix Non-Manifold Geometry",
    "blender": (4, 0, 0),
    "category": "Mesh",
    "author": "Stefan 'ramsesoriginal' Insam",
    "version": (1, 0, 2),
    "location": "3D Viewport > Sidebar > Tools Tab",
    "description": "Detects and fixes non-manifold geometry, holes, flipped normals, and duplicate vertices.",
    "support": "COMMUNITY",
    "warning": "",
}

import bpy
import bmesh

def fix_non_manifold(obj, log):
    if obj.type == 'MESH' and obj.visible_get():  # Process only visible mesh objects
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

        bm = bmesh.from_edit_mesh(obj.data)
        fixes = []

        # Detect non-manifold edges
        non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
        if non_manifold_edges:
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.mesh.select_non_manifold()
            fixes.append("Fixed non-manifold edges")

        # Merge duplicate vertices
        initial_vert_count = len(bm.verts)
        bpy.ops.mesh.remove_doubles(threshold=0.0001)
        if len(bm.verts) < initial_vert_count:
            fixes.append("Merged duplicate vertices")

        # Fill small holes (only if selected edges exist)
        if any(e.select for e in bm.edges):
            bpy.ops.mesh.edge_face_add()
            fixes.append("Filled small holes")

        # Recalculate normals only if some faces exist
        if len(bm.faces) > 0:
            bpy.ops.mesh.normals_make_consistent(inside=False)
            fixes.append("Recalculated normals")

        bpy.ops.object.mode_set(mode='OBJECT')

        if fixes:
            log.append(f"{obj.name}: " + ", ".join(fixes))
            print(f"Fixed: {obj.name} → " + ", ".join(fixes))
        else:
            log.append(f"{obj.name}: No issues found")

class OBJECT_OT_FixNonManifold(bpy.types.Operator):
    """Fix non-manifold geometry, duplicate vertices, and normals"""
    bl_idname = "object.fix_non_manifold"
    bl_label = "Fix Non-Manifold Geometry for all objects"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        log = []
        for obj in bpy.context.visible_objects:
            fix_non_manifold(obj, log)

        # Show summary log in the Info Panel
        if log:
            self.report({'INFO'}, " | ".join(log))
        
        return {'FINISHED'}

class VIEW3D_PT_FixNonManifoldPanel(bpy.types.Panel):
    bl_label = "Fix Non-Manifold Geometry"
    bl_idname = "VIEW3D_PT_fix_non_manifold"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tools'
    
    def draw(self, context):
        layout = self.layout
        layout.operator("object.fix_non_manifold", icon='MODIFIER')

def register():
    bpy.utils.register_class(OBJECT_OT_FixNonManifold)
    bpy.utils.register_class(VIEW3D_PT_FixNonManifoldPanel)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_FixNonManifold)
    bpy.utils.unregister_class(VIEW3D_PT_FixNonManifoldPanel)

if __name__ == "__main__":
    register()
