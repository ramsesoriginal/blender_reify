bl_info = {
    "name": "Add Edge Loop to Cone",
    "blender": (4, 0, 0),
    "category": "Mesh",
    "author": "Stefan 'ramsesoriginal' Insam",
    "version": (1, 0, 1),
    "location": "3D Viewport > Sidebar > Tools Tab",
    "description": "Adds an edge loop near the apex of cone objects to allow further loop cuts.",
    "support": "COMMUNITY",
    "warning": "",
}

import bpy
import bmesh

class OBJECT_OT_AddEdgeLoopToCone(bpy.types.Operator):
    """Adds an edge loop to a cone by bisecting edges from apex to base"""
    bl_idname = "mesh.add_edge_loop_to_cone"
    bl_label = "Add Edge Loop to Cone"
    bl_options = {'REGISTER', 'UNDO'}

    fraction: bpy.props.FloatProperty(
        name="Fraction",
        description="Fraction of edge length from apex to cut",
        default=0.5,
        min=0.01, max=0.99
    )
    
    auto_detect: bpy.props.BoolProperty(
        name="Auto Detect Apex",
        description="Automatically detect the apex or use selected vertex",
        default=True
    )

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)

        if self.auto_detect:
            # Auto-detect mode: Find the apex (highest vertex)
            apex_vert = max(bm.verts, key=lambda v: v.co.z)
        else:
            # Manual mode: Use the selected vertex
            selected_verts = [v for v in bm.verts if v.select]
            if len(selected_verts) != 1:
                self.report({'ERROR'}, "Select exactly one vertex as apex")
                return {'CANCELLED'}
            apex_vert = selected_verts[0]
        
        # Find all edges connected to the apex
        connected_edges = [e for e in bm.edges if apex_vert in e.verts]
        
        if not connected_edges:
            self.report({'ERROR'}, "No edges connected to the apex found")
            return {'CANCELLED'}

        new_verts = []
        for edge in connected_edges:
            v1, v2 = edge.verts
            other_vert = v1 if v2 == apex_vert else v2
            
            # Calculate new vertex position along the edge
            new_co = apex_vert.co.lerp(other_vert.co, self.fraction)
            new_vert = bm.verts.new(new_co)
            new_verts.append(new_vert)
            
            # Split the edge at the new vertex
            bm.edges.new([apex_vert, new_vert])
            bm.edges.new([new_vert, other_vert])
            bm.edges.remove(edge)
        
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Added edge loop at fraction {self.fraction}")
        return {'FINISHED'}

class VIEW3D_PT_AddEdgeLoopToConePanel(bpy.types.Panel):
    """Panel for adding edge loops to cones"""
    bl_label = "Add Edge Loop to Cone"
    bl_idname = "VIEW3D_PT_add_edge_loop_to_cone"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tools'
    
    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.add_edge_loop_to_cone", icon='MESH_CIRCLE')

def register():
    bpy.utils.register_class(OBJECT_OT_AddEdgeLoopToCone)
    bpy.utils.register_class(VIEW3D_PT_AddEdgeLoopToConePanel)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_AddEdgeLoopToCone)
    bpy.utils.unregister_class(VIEW3D_PT_AddEdgeLoopToConePanel)

if __name__ == "__main__":
    register()
