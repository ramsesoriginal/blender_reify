bl_info = {
    "name": "Gothic Architecture Tools",
    "blender": (4, 0, 0),
    "category": "Add Mesh",
    "author": "Stefan 'ramsesoriginal' Insam",
    "version": (1, 0, 1),
    "location": "3D Viewport > Sidebar > Gothic Tools",
    "description": "Adds tools for modeling Gothic architectural elements.",
    "support": "COMMUNITY",
    "warning": "Work in progress – tweak parameters to taste",
}

import bpy
import bmesh
from mathutils import Vector
import math
import time

def bezier_curve(t, p0, p1, p2, p3):
    """ Computes a cubic Bézier curve value for parameter t. """
    u = 1 - t
    return (u ** 3 * p0 +
            3 * u ** 2 * t * p1 +
            3 * u * t ** 2 * p2 +
            t ** 3 * p3)

def fast_in_out_bezier(t, sharpness_in=0.5, sharpness_out=0.5):
    """
    Computes a fast-in, fast-out cubic Bézier easing function.
    
    :param t: The input value in [0,1].
    :param sharpness: The sharpness of the curve (0 = diagonal, 1 = very sharp curves).
    :return: The eased value.
    """
    # Clamp inputs to valid range
    t = max(0, min(1, t))
    sharpness_in = max(-2, min(2, sharpness_in))
    sharpness_out = max(-2, min(2, sharpness_out))

    # Control points for the Bézier curve
    p0, p3 = 0, 1  # Start and end
    p1 = sharpness_in  # Control point 1 (affects fast-in)
    p2 = sharpness_out  # Control point 2 (affects fast-out)

    return bezier_curve(t, p0, p1, p2, p3)

# Function to rotate an edge to align with a given vector
def align_edge_to_vector(edge, target_vector):
    v1, v2 = edge.verts
    edge_vector = (v2.co - v1.co).normalized()
    target_vector = target_vector.normalized()

    if edge_vector.length == 0:
        return  # Avoid issues with zero-length vectors

    # Determine if we need to flip the target direction
    if edge_vector.angle(target_vector, 0) > (90.0 * (3.14159265 / 180.0)):  # Convert degrees to radians
        target_vector = -target_vector  # Flip the direction

    # Compute rotation quaternion
    rotation_quat = edge_vector.rotation_difference(target_vector)

    # Compute midpoint of the edge
    midpoint = (v1.co + v2.co) / 2

    # Rotate vertices around the midpoint
    v1.co = midpoint + rotation_quat @ (v1.co - midpoint)
    v2.co = midpoint + rotation_quat @ (v2.co - midpoint)

def get_window_faces_between(first, second, new_faces, old_faces):
    # Helper: returns True if face touches the given edge.
    def face_touches(face, edge):
        return edge in face.edges

    # Helper: returns True if the faces share an edge.
    def edge_between(face, other):
        for e in face.edges:
            if face_touches(other, e):
                return e
        return None


    # Helper: For a quad face, return the edge opposite to a given boundary edge.
    def get_opposite_edge(face, boundary_edge):
        # For a quad, the opposite edge is the one that does not share any vertex with the boundary_edge.
        for e in face.edges:
            if e == boundary_edge:
                continue
            # If e shares no vertex with boundary_edge, it's the opposite.
            if not set(e.verts) & set(boundary_edge.verts):
                return e
        return None

    # Helper: For a quad face, return the face opposite to a given boundary edge.
    def get_opposite_face(face, boundary_edge):
        e = get_opposite_edge(face, boundary_edge)
        if not e:
            return None
        return [f for f in e.link_faces if f != face][0]

    def get_next_face(face, prev_face):
        e = edge_between(face, prev_face)
        if e:
            return get_opposite_face(face, e)
        return None
    
    start_faces = [f for f in new_faces if face_touches(f, first)]
    if start_faces:
        starting_boundary = first
        ending_boundary = second
        start_face = start_faces[0]
    else:
        start_faces = [f for f in new_faces if face_touches(f, second)]
        if start_faces:
            starting_boundary = second
            ending_boundary = first
            start_face = start_faces[0]
        else:
            # No new face touches either boundary.
            return []

    faces_between = [start_face]
    next_face = get_opposite_face(start_face, starting_boundary)
    while next_face:
        faces_between.append(next_face)
        next_face = get_next_face(next_face, faces_between[-2])
        if face_touches(next_face, ending_boundary):
            break
        if next_face in faces_between:
            break
        if next_face in old_faces:
            break
    return faces_between



def loopcut_between(first, second, faces, edges, boundary_edges, all_edges, bm, obj, n=1, report=None):
    face = None
    for f in faces:
        if first in f.edges and second in f.edges:
            face = f
    other_edges = [e for e in face.edges if e not in (first, second)]
    ref_edge = other_edges[0]
    
    existing_faces = set(bm.faces)
    existing_edges = set(bm.edges)

    bmesh.update_edit_mesh(obj.data)
    loopcut(edge_index=ref_edge.index, number_cuts=n)
    bmesh.update_edit_mesh(obj.data)

    new_faces = set(bm.faces) - existing_faces
    new_edges = set(bm.edges) - existing_edges

    new_window_faces = get_window_faces_between(first, second, new_faces, new_edges)
    if report is not None:
        report({'INFO'}, "new_window_faces: " + ", ".join(repr(f) for f in new_window_faces))
    for f in new_window_faces:
        faces.append(f)

    new_window_edges = []
    for e in new_edges:
        if any(f in faces for f in e.link_faces):
            all_edges.add(e)
            if any(f not in faces for f in e.link_faces):
                boundary_edges.add(e)
            else:
                new_window_edges.append(e)
                edges.append(e)

    return (new_window_faces, new_window_edges)

def loopcut(edge_index, number_cuts=1):
    cutting_data = {
        "number_cuts"  : number_cuts,
        "object_index" : 0,
        "edge_index"   : edge_index,
    }
    bpy.ops.mesh.loopcut_slide(MESH_OT_loopcut=cutting_data)

    # Short delay to allow Blender to finish processing
    time.sleep(0.005)

    # Force Blender to process updates before continuing
    bpy.context.view_layer.update()

def select_faces(faces, deselect_others=True):
    """
    Selects the given faces in Edit Mode.

    :param faces: A list of faces (bmesh.types.BMFace) to select.
    :param deselect_others: If True, deselects all other faces first.
    """
    obj = bpy.context.object
    if obj is None or obj.type != 'MESH':
        print("Error: No active mesh object selected.")
        return

    # Ensure we're in Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')

    # Get the mesh data
    bm = bmesh.from_edit_mesh(obj.data)

    # Optionally deselect all faces first
    if deselect_others:
        for f in bm.faces:
            f.select = False

    # Select only the given faces
    for face in faces:
        face.select = True

    # Update mesh selection
    bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=False)

class MESH_OT_AddDivineFlyingButtress(bpy.types.Operator):
    """Create a Divine Flying Buttress, inspired by great Gothic cathedrals"""
    bl_idname = "mesh.add_divine_flying_buttress"
    bl_label = "Add Divine Flying Buttress"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Pier parameters
    pier_width: bpy.props.FloatProperty(name="Pier Width", default=1.0, min=0.1, max=5.0)
    pier_depth: bpy.props.FloatProperty(name="Pier Depth", default=1.0, min=0.1, max=5.0)
    pier_height: bpy.props.FloatProperty(name="Pier Height", default=5.0, min=1.0, max=20.0)
    
    # Arch parameters
    arch_span: bpy.props.FloatProperty(name="Arch Span", default=4.0, min=1.0, max=20.0)
    arch_height: bpy.props.FloatProperty(name="Arch Height", default=3.0, min=0.1, max=10.0)
    arch_thickness: bpy.props.FloatProperty(name="Arch Thickness", default=0.5, min=0.1, max=5.0)
    arch_segments: bpy.props.IntProperty(name="Arch Segments", default=12, min=4, max=50)
    
    def execute(self, context):
        # Create a new mesh and object
        mesh = bpy.data.meshes.new("Divine_Flying_Buttress")
        obj = bpy.data.objects.new("Divine_Flying_Buttress", mesh)
        bpy.context.collection.objects.link(obj)
        
        bm = bmesh.new()
        
        # --- Create the vertical pier as a box ---
        w = self.pier_width
        d = self.pier_depth
        h = self.pier_height
        # Define 8 vertices for the box
        v0 = bm.verts.new(Vector((-w/2, -d/2, 0)))
        v1 = bm.verts.new(Vector((w/2, -d/2, 0)))
        v2 = bm.verts.new(Vector((w/2, d/2, 0)))
        v3 = bm.verts.new(Vector((-w/2, d/2, 0)))
        v4 = bm.verts.new(Vector((-w/2, -d/2, h)))
        v5 = bm.verts.new(Vector((w/2, -d/2, h)))
        v6 = bm.verts.new(Vector((w/2, d/2, h)))
        v7 = bm.verts.new(Vector((-w/2, d/2, h)))
        
        # Create faces for the pier
        bm.faces.new((v0, v1, v2, v3))
        bm.faces.new((v4, v5, v6, v7))
        bm.faces.new((v0, v1, v5, v4))
        bm.faces.new((v1, v2, v6, v5))
        bm.faces.new((v2, v3, v7, v6))
        bm.faces.new((v3, v0, v4, v7))
        
        # --- Create the arch ---
        # Arch starts at the right center top of the pier.
        start = Vector((w/2, 0, h))
        end = Vector((w/2 + self.arch_span, 0, h))
        N = self.arch_segments
        arch_points_front = []
        for i in range(N + 1):
            t = i / N
            # Using a quadratic function to simulate a pointed (Gothic) arch:
            # z = h + arch_height*(1 - (2*t - 1)**2) gives a pointed profile with a maximum at t=0.5
            z = h + self.arch_height * (1 - (2*t - 1)**2)
            x = start.x + t * (end.x - start.x)
            y = 0
            arch_points_front.append(Vector((x, y, z)))
        
        # For thickness, duplicate the arch points offset in the negative Y direction
        arch_points_back = [p + Vector((0, -self.arch_thickness, 0)) for p in arch_points_front]
        
        # Create vertices along the arch curves
        arch_front_verts = [bm.verts.new(p) for p in arch_points_front]
        arch_back_verts = [bm.verts.new(p) for p in arch_points_back]
        
        # Connect the arch front and back curves (edges)
        for i in range(N):
            bm.edges.new((arch_front_verts[i], arch_front_verts[i+1]))
            bm.edges.new((arch_back_verts[i], arch_back_verts[i+1]))
        
        # Create faces between the two curves to form a solid arch rib
        for i in range(N):
            bm.faces.new((arch_front_verts[i], arch_front_verts[i+1],
                          arch_back_verts[i+1], arch_back_verts[i]))
        
        # Connect the arch to the pier: connect the start of the arch with the top face of the pier
        # Assume the top face of the pier on the right side is defined by v5 and v6.
        try:
            bm.faces.new((v5, arch_front_verts[0], arch_back_verts[0], v6))
        except Exception as e:
            # Face might already exist or be non-planar – skip if error occurs.
            pass
        
        bm.to_mesh(mesh)
        bm.free()
        
        self.report({'INFO'}, "Divine Flying Buttress created")
        return {'FINISHED'}

class MESH_OT_AddFlyingButtress(bpy.types.Operator):
    """Generate a flying buttress with customizable parameters"""
    bl_idname = "mesh.add_flying_buttress"
    bl_label = "Add Flying Buttress"
    bl_options = {'REGISTER', 'UNDO'}
    
    height: bpy.props.FloatProperty(name="Height", default=3.0, min=1.0, max=10.0)
    width: bpy.props.FloatProperty(name="Width", default=0.5, min=0.1, max=3.0)
    depth: bpy.props.FloatProperty(name="Depth", default=1.0, min=0.1, max=5.0)
    curvature: bpy.props.FloatProperty(name="Curvature", default=0.3, min=0.0, max=1.0, description="Arch curvature factor")

    def execute(self, context):
        mesh = bpy.data.meshes.new("Flying_Buttress")
        obj = bpy.data.objects.new("Flying_Buttress", mesh)
        bpy.context.collection.objects.link(obj)

        bm = bmesh.new()

        # Define base and arch curve
        num_segments = 8
        base_v1 = bm.verts.new(Vector((-self.width / 2, 0, 0)))
        base_v2 = bm.verts.new(Vector((self.width / 2, 0, 0)))

        arch_verts = []
        for i in range(num_segments + 1):
            t = i / num_segments
            x = (t - 0.5) * self.width
            y = self.depth * (t ** 2)  # Parabolic curve
            z = self.height * (1 - sin(t * pi / 2) * self.curvature)
            arch_verts.append(bm.verts.new(Vector((x, y, z))))

        # Connect edges
        for i in range(len(arch_verts) - 1):
            bm.edges.new((arch_verts[i], arch_verts[i + 1]))

        bm.edges.new((base_v1, arch_verts[0]))
        bm.edges.new((base_v2, arch_verts[-1]))

        bm.to_mesh(mesh)
        bm.free()

        return {'FINISHED'}

class MESH_OT_ConvertInsetToLancetWindow(bpy.types.Operator):
    """Convert selected inset window faces into a smooth Lancet (pointed) window shape"""
    bl_idname = "mesh.convert_inset_to_lancet_window"
    bl_label = "Convert Inset to Lancet Window (Advanced)"
    bl_options = {'REGISTER', 'UNDO'}

    # User-adjustable parameters:
    curve_segments:  bpy.props.IntProperty(
        name="Curve Segments",
        description="Total number of segments along the curved wall",
        default=0,
        min=0,
        max=40
    )
    start_fraction:  bpy.props.FloatProperty(
        name="Curve Start Fraction",
        description="Fraction from the top at which the wall begins to curve (e.g. 0.2 = 20%)",
        default=0.6,
        min=0.0,
        max=1.0
    )
    sharpness_in:  bpy.props.FloatProperty(
        name="In",
        description="Sharpness factor of the curve (0 = straight up, 3 = nearly horizontal)",
        default=0,
        min=-2.0,
        max=3.0
    )
    sharpness_out:  bpy.props.FloatProperty(
        name="Out",
        description="Sharpness factor of the curve (0 = gentle angle, 3 = straight up)",
        default=0,
        min=-1.0,
        max=3.0
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        existing_faces = set(bm.faces)
        existing_edges = set(bm.edges)

        # --- STEP 1: Identify the window's boundary and top edge ---
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'ERROR'}, "No faces selected")
            return {'CANCELLED'}
        
        # Boundary edges: edges that connect the selected faces to the rest of the mesh
        boundary_edges = set()
        selected_edges = set()
        for e in bm.edges:
            linked_selected_faces = sum([f in selected_faces for f in e.link_faces])
            if linked_selected_faces > 0:
                selected_edges.add(e)
                if linked_selected_faces != 2 :
                    boundary_edges.add(e)

        if not boundary_edges:
            self.report({'ERROR'}, "No boundary edges found")
            return {'CANCELLED'}

        # Determine top boundary: edges with highest average Z
        def edge_avg_z(edge):
            return sum(v.co.z for v in edge.verts) / len(edge.verts)
        max_z = max(edge_avg_z(e) for e in selected_edges)
        min_z = min(edge_avg_z(e) for e in selected_edges)
        height = max_z - min_z
        tol = 0.001
        top_edges = [e for e in selected_edges if abs(edge_avg_z(e) - max_z) < tol and e not in boundary_edges]
        original_wall_edges = [e for e in selected_edges if e not in top_edges and e not in boundary_edges]
        top_edge = list(top_edges)[0]

        def find_perpendicular_vector(edges):
            edges = list(edges)  # Convert set to list
            best_vector = None
            best_magnitude = 0  # Track the strongest perpendicular direction
            
            for i in range(len(edges)):
                vec1 = edges[i].verts[1].co - edges[i].verts[0].co
                
                for j in range(i + 1, len(edges)):
                    vec2 = edges[j].verts[1].co - edges[j].verts[0].co
                    cross_product = vec1.cross(vec2)
                    magnitude = cross_product.length
                    
                    if magnitude > best_magnitude:
                        best_magnitude = magnitude
                        best_vector = cross_product.normalized()

            return best_vector if best_vector else None  # Return the strongest perpendicular found

        forward = find_perpendicular_vector(boundary_edges)

        # Compute a perpendicular in the XY plane (local left/right)
        perp = Vector((-forward.y, forward.x, 0)).normalized()

        def edge_sort_key(edge):
                v1, v2 = edge.verts
                midpoint = (v1.co + v2.co) / 2  # Find the midpoint
                projected_value = midpoint.dot(perp)  # Projection onto direction vector
                return projected_value

        if len(top_edges) > 1:
            top_edges_sorted = sorted(top_edges, key=edge_sort_key)

            middle_index = len(top_edges_sorted) // 2
            top_edge = top_edges_sorted[middle_index]

            if len(top_edges) % 2 == 0:
                first = top_edge
                second = top_edges_sorted[middle_index-1]

                loopcut_between(first, second, selected_faces, top_edges, boundary_edges, selected_edges, bm, obj, report=self.report)

                top_edges_sorted = sorted(top_edges, key=edge_sort_key)

                middle_index = len(top_edges_sorted) // 2
                top_edge = top_edges_sorted[middle_index]


        align_edge_to_vector(top_edge, forward)


        # Get the top edge vertices and compute their center.
        top_edge_verts = [v.co.copy() for v in top_edge.verts]
        top_center = sum(top_edge_verts, Vector()) / len(top_edge_verts)


        def distance_to_center(edge):
            edge_center = sum((v.co for v in edge.verts), Vector()) / len(edge.verts)
            distance = (top_center - edge_center).length
            return -distance



        # --- STEP 2: Partition wall edges using the top edge as reference ---
        wall_edges = original_wall_edges + [e for e in top_edges if e != top_edge]
        wall_edges_sorted = sorted(wall_edges, key=edge_sort_key)
        left_edges = []
        right_edges = []
        for e in wall_edges:
            center = sum((v.co for v in e.verts), Vector()) / len(e.verts)
            diff = center - top_center
            # Use dot product with 'perp' to decide left/right:
            if diff.dot(perp) > 0:
                left_edges.append(e)
            else:
                right_edges.append(e)
        

        def sort_vertically(walls):
            return sorted(walls, key=lambda e: (edge_avg_z(e), distance_to_center(e)))

        # --- STEP 3: Ensure sufficient segmentation for smooth curving ---
        # We now gather all wall vertices (excluding those on the top edge).

        def subdivide(side, rev=False):
            if not side:
                return
            if self.curve_segments<1:
                return
            sorted_walls = sort_vertically(side)
            first = sorted_walls[-1]
            second = top_edge
            if rev:
                first, second = second, first
            loopcut_between(first, second, selected_faces, side, boundary_edges, selected_edges, bm, obj, self.curve_segments, report=self.report)
 

        subdivide(left_edges)
        subdivide(right_edges, True)

        # --- STEP 4: Curve the wall vertices ---
        # For each wall vertex, compute its relative vertical position f (0=bottom, 1=top).
        # For f below start_fraction, no change; for f above, add an outward bulge.

        def move_to(wall, goal):
            wall_center = sum((v.co for v in wall.verts), Vector()) / len(e.verts)
            movement_vector = goal - wall_center
            for v in wall.verts:
                v.co.x += movement_vector.x
                v.co.y += movement_vector.y
                v.co.z += movement_vector.z
            bmesh.update_edit_mesh(obj.data)

        def move_vertically(wall, goal):
            wall_center = sum((v.co for v in wall.verts), Vector()) / len(e.verts)
            move_to(wall, Vector((wall_center.x,wall_center.y,goal)))

        def space_vertically(walls):
            if not walls:
                return
            for w in walls:
                align_edge_to_vector(w, forward)
            end_of_straight = walls[0]
            curve=[]
            if len(walls) > 1:
                sorted_walls = sort_vertically(walls)
                end_of_straight, *curve = sorted_walls
            curve_start_height = min_z + height * self.start_fraction
            move_vertically(end_of_straight, curve_start_height)
            curve_height = max_z - curve_start_height
            steps = len(curve) + 1
            i = 1
            for w in curve:
                fraction = i/steps # fast_in_out_bezier(i/steps, self.sharpness)

                # self.report({'INFO'}, 'fraction, curve_start_height, curve_height: ' + repr(fraction) + " " + repr(curve_start_height) + " " + repr(curve_height))
                move_vertically(w, curve_start_height + fraction * curve_height)
                i+=1

        
        space_vertically(right_edges)
        space_vertically(left_edges)

        def space_horizontally(walls, direction):
            """
            Spaces the given walls along the given direction based on the same logic as vertical spacing.
            """
            if not walls:
                return

            end_of_straight = walls[0]
            curve = []

            if len(walls) > 1:
                sorted_walls = sort_vertically(walls)
                end_of_straight, *curve = sorted_walls

            min_pos = sum((v.co for v in end_of_straight.verts), Vector()) / len(end_of_straight.verts)
            max_pos = sum((v.co for v in top_edge.verts), Vector()) / len(top_edge.verts)

            min_pos.z = 0
            max_pos.z = 0

            distance = (max_pos - min_pos).length

            steps = len(curve) + 1
            i = 1

            for w in curve:
                fraction = fast_in_out_bezier(i / steps, self.sharpness_in, self.sharpness_out)
                xypos = min_pos + fraction * distance * direction
                height = (sum((v.co for v in w.verts), Vector()) / len(e.verts)).z
                move_to(w, Vector((xypos.x, xypos.y, height)))
                i += 1

        space_horizontally(right_edges, perp)
        space_horizontally(left_edges, -perp)

        bmesh.update_edit_mesh(obj.data)
        select_faces(selected_faces)
        self.report({'INFO'}, "Converted inset to Lancet Window (Advanced)")
        return {'FINISHED'}


class GOTHIC_PT_MainPanel(bpy.types.Panel):
    bl_label = "Gothic Architecture"
    bl_idname = "GOTHIC_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gothic Tools'
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Create Gothic Elements:")
        layout.operator("mesh.add_gothic_arch", icon='MESH_CIRCLE')
        layout.operator("mesh.add_gothic_vault", icon='MESH_GRID')
        layout.operator("mesh.add_flying_buttress", icon='MESH_CUBE')
        layout.operator("mesh.add_divine_flying_buttress", icon='MODIFIER')
        layout.operator("mesh.add_tracery", icon='MESH_PLANE')
        layout.operator("mesh.add_gargoyle", icon='MESH_MONKEY')
        layout.operator("mesh.add_spire", icon='MESH_CONE')
        layout.separator()
        layout.label(text="Window Tools:")
        layout.operator("mesh.convert_inset_to_lancet_window", icon='MOD_SOLIDIFY')


# Placeholder Operators
class MESH_OT_AddGothicArch(bpy.types.Operator):
    bl_idname = "mesh.add_gothic_arch"
    bl_label = "Add Pointed Arch"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        self.report({'INFO'}, "Pointed Arch created (placeholder)")
        return {'FINISHED'}

class MESH_OT_AddGothicVault(bpy.types.Operator):
    bl_idname = "mesh.add_gothic_vault"
    bl_label = "Add Pointed Rib Vault"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        self.report({'INFO'}, "Pointed Rib Vault created (placeholder)")
        return {'FINISHED'}

class MESH_OT_AddTracery(bpy.types.Operator):
    bl_idname = "mesh.add_tracery"
    bl_label = "Add Tracery"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        self.report({'INFO'}, "Tracery created (placeholder)")
        return {'FINISHED'}

class MESH_OT_AddGargoyle(bpy.types.Operator):
    bl_idname = "mesh.add_gargoyle"
    bl_label = "Add Gargoyle"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        self.report({'INFO'}, "Gargoyle created (placeholder)")
        return {'FINISHED'}

class MESH_OT_AddSpire(bpy.types.Operator):
    bl_idname = "mesh.add_spire"
    bl_label = "Add Spire"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        self.report({'INFO'}, "Spire created (placeholder)")
        return {'FINISHED'}

classes = [
    GOTHIC_PT_MainPanel,
    MESH_OT_AddGothicArch,
    MESH_OT_AddGothicVault,
    MESH_OT_AddFlyingButtress,
    MESH_OT_AddTracery,
    MESH_OT_AddGargoyle,
    MESH_OT_AddSpire,
    MESH_OT_AddDivineFlyingButtress,
    MESH_OT_ConvertInsetToLancetWindow,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
