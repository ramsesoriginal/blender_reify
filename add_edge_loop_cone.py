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
import math
from mathutils import Vector

class MESH_OT_AddEdgeLoopToCone(bpy.types.Operator):
    """Convert a fan of tris (selected by choosing the apex) into a Lancet Window"""
    bl_idname = "mesh.add_edge_loop_to_cone"
    bl_label = "Adds an edge loop to a cone"
    bl_options = {'REGISTER', 'UNDO'}

    fraction: bpy.props.FloatProperty(
        name="Spike Fraction",
        description="Fraction along each spike (apex to border) at which to cut (0 = at apex, 1 = at border)",
        default=0.5,
        min=0.01,
        max=0.99
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}

        # Ensure exactly one vertex is selected (the apex)
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        selected_verts = [v for v in bm.verts if v.select]
        if len(selected_verts) != 1:
            self.report({'ERROR'}, "Please select exactly one vertex as the apex.")
            return {'CANCELLED'}

        apex = selected_verts[0]

        # Collect all faces that share the apex; assume they are triangles.
        fan_faces = [f for f in bm.faces if apex in f.verts]
        if not fan_faces:
            self.report({'ERROR'}, "No faces found that share the apex.")
            return {'CANCELLED'}

        # Build the set of border vertices (non-apex vertices from the fan).
        border_verts = set()
        for f in fan_faces:
            for v in f.verts:
                if v != apex:
                    border_verts.add(v)
        if len(border_verts) < 2:
            self.report({'ERROR'}, "Not enough border vertices found.")
            return {'CANCELLED'}

        border_verts = list(border_verts)

        # Compute the center of the border vertices.
        border_center = sum((v.co for v in border_verts), Vector()) / len(border_verts)

        # The main direction: from apex to border center.
        main_direction = (border_center - apex.co).normalized()

        # Pick a reference vector:
        # Use the vector from the apex to the first border vertex, projected onto the plane perpendicular to main_direction.
        ref_vec = border_verts[0].co - apex.co
        ref_vec_projected = ref_vec - (ref_vec.dot(main_direction)) * main_direction
        ref_vec_projected.normalize()

        # Compute a perpendicular vector in that plane.
        perp_ref = main_direction.cross(ref_vec_projected)

        # Sort border vertices around the apex in the XY plane.
        def angle_from_apex(v):
            vec = v.co - apex.co
            # Project vec onto the plane perpendicular to main_direction.
            proj = vec - (vec.dot(main_direction)) * main_direction
            # Compute the angle using atan2: the y-coordinate is the projection on perp_ref, 
            # and the x-coordinate is the projection on ref_vec_projected.
            angle = math.atan2(proj.dot(perp_ref), proj.dot(ref_vec_projected))
            return angle

        border_verts.sort(key=angle_from_apex)

        # Create a dictionary to store the new "middle" vertex on each spike.
        middle_verts = {}
        # For each border vertex, find the edge from apex to that border vertex.
        for bv in border_verts:
            spike_edge = None
            for e in bv.link_edges:
                if apex in e.verts:
                    spike_edge = e
                    break
            if spike_edge is None:
                self.report({'ERROR'}, "Could not find a spike edge for a border vertex.")
                return {'CANCELLED'}
            # Compute the new vertex along this edge.
            new_co = apex.co.lerp(bv.co, self.fraction)
            new_vert = bm.verts.new(new_co)
            middle_verts[bv] = new_vert

        bm.verts.index_update()
        bm.edges.index_update()
        bmesh.update_edit_mesh(obj.data)

        # Create the middle loop: sorted in the same order as border_verts.
        middle_loop = [middle_verts[bv] for bv in border_verts]

        # Remove the original spike edges (edges connecting the apex to each border vertex)
        spike_edges_to_delete = []
        for bv in border_verts:
            # Find an edge between the apex and the border vertex.
            for e in bv.link_edges:
                if apex in e.verts:
                    spike_edges_to_delete.append(e)
                    break  # Only remove one spike per border vertex

        # Remove those edges from the BMesh.
        for e in spike_edges_to_delete:
            bm.edges.remove(e)

        bmesh.update_edit_mesh(obj.data)

        # Create faces: 
        # 1. Fill the central fan: triangles from apex to consecutive middle verts.
        for i in range(len(middle_loop)):
            v1 = apex
            v2 = middle_loop[i]
            v3 = middle_loop[(i+1) % len(middle_loop)]
            try:
                bm.faces.new((v1, v2, v3))
            except Exception:
                pass

        # 2. Fill the outer ring: quads from border to middle loop.
        for i in range(len(middle_loop)):
            bv1 = border_verts[i]
            bv2 = border_verts[(i+1) % len(border_verts)]
            mv1 = middle_loop[i]
            mv2 = middle_loop[(i+1) % len(middle_loop)]
            try:
                bm.faces.new((mv1, bv1, bv2, mv2))
            except Exception:
                pass

        bmesh.update_edit_mesh(obj.data)

        for f in bm.faces:
            f.select = False

        # Select faces that touch any of the middle vertices
        for f in bm.faces:
            if any(v in middle_loop for v in f.verts):
                f.select = True
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=False)

        bpy.ops.mesh.normals_make_consistent(inside=False)
        bmesh.update_edit_mesh(obj.data)

        for f in bm.faces:
            f.select = False

        apex.select = True
        
        bmesh.update_edit_mesh(obj.data)

        self.report({'INFO'}, "Added Edge Loop To Cone")
        return {'FINISHED'}


# **New Panel for the Sidebar**
class VIEW3D_PT_AddEdgeLoopToConePanel(bpy.types.Panel):
    """Creates a Panel in the Sidebar under 'Tools'"""
    bl_label = "Lancet Window Tool"
    bl_idname = "VIEW3D_PT_add_edge_loop_to_cone_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tools'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Add an Edge Loop to a Cone")
        layout.operator("mesh.add_edge_loop_to_cone", icon='MESH_CIRCLE')


# **Register and Unregister Functions**
def register():
    bpy.utils.register_class(MESH_OT_AddEdgeLoopToCone)
    bpy.utils.register_class(VIEW3D_PT_AddEdgeLoopToConePanel)

def unregister():
    bpy.utils.unregister_class(MESH_OT_AddEdgeLoopToCone)
    bpy.utils.unregister_class(VIEW3D_PT_AddEdgeLoopToConePanel)

if __name__ == "__main__":
    register()

