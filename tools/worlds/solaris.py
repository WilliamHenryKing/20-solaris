"""SOLARIS: an inhabited courtyard house opening onto a Mediterranean garden.
Original metre-scale architecture, furniture, foreground dressing and a continuous planted garden.
Root supplies CC0 PBR materials/HDRI and owns all renders. No image generation or rendering here.
"""
import math
import random
import bpy
from mathutils import Vector
from mathutils.geometry import interpolate_bezier
from world_common import (baked_cloth, cube, cylinder, area, sun, camera, annulus, curved_wall,
                          lathe_vessel, leaf_material, material, branch, plant, rounded_box, poly_curve)

# Courtyard slab cells left open for the olive's planting pit (slab centres, metres).
PLANTING_PIT = {(-4, 2), (-3, 2)}


def move(obj, delta):
    obj.location += Vector(delta)
    return obj


def physical_uv(obj):
    """Metre-scaled planar UVs for authored meshes and imported geometry helpers."""
    mesh=obj.data
    layer=mesh.uv_layers.active or mesh.uv_layers.new(name='SOLARIS / physical metres')
    for face in mesh.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]))
        for index in face.loop_indices:
            co=mesh.vertices[mesh.loops[index].vertex_index].co
            layer.data[index].uv=(co.y,co.z) if axis==0 else ((co.x,co.z) if axis==1 else (co.x,co.y))
    return obj


def aggregate(name, verts, faces, mat, smooth=False):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    physical_uv(obj)
    if smooth:
        for face in obj.data.polygons:face.use_smooth=True
    return obj


def pebble_patch(name, centre, width, depth, mat, seed=1, count=150):
    rng=random.Random(seed)
    verts,faces=[],[]
    # Rounded low-poly pebbles aggregated once; their scale belongs in the garden.
    for _ in range(count):
        x=centre[0]+rng.uniform(-width/2,width/2)
        y=centre[1]+rng.uniform(-depth/2,depth/2)
        z=centre[2]
        r=rng.uniform(.018,.052)
        start=len(verts)
        rings=5
        segments=8
        for j in range(rings):
            phi=math.pi*(j+.15)/(rings-.7)
            for i in range(segments):
                a=i/segments*math.tau
                verts.append((x+math.cos(a)*math.sin(phi)*r,y+math.sin(a)*math.sin(phi)*r*.8,z+math.cos(phi)*r*.55+r*.2))
        for j in range(rings-1):
            for i in range(segments):
                k=(i+1)%segments
                faces.append((start+j*segments+i,start+j*segments+k,start+(j+1)*segments+k,start+(j+1)*segments+i))
    return aggregate(name,verts,faces,mat,True)


def water_surface(m):
    verts=[]
    faces=[]
    nx,ny=30,90
    for j in range(ny+1):
        for i in range(nx+1):
            x=.65+i/nx*2.8
            y=2.1+j/ny*9.2
            z=-.07+.0019*math.sin(x*12+y*5)+.0011*math.sin(y*18-x*9)
            verts.append((x,y,z))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i
            faces.append((a,a+1,a+nx+2,a+nx+1))
    aggregate('Pool / true gently rippled water interface',verts,faces,m['water'],True)
    cube('Pool limestone basin bottom',(2.05,6.7,-.58),(2.84,9.24,.16),m['stone'],.012)
    for x in [.57,3.53]:
        cube('Pool continuous stone coping',(x,6.7,-.005),(.18,9.6,.12),m['stone'],.014)
        cube('Pool below-water side lining',(x,6.7,-.31),(.12,9.6,.5),m['stone'],.008)
    for y in [2.02,11.38]:
        cube('Pool stone end coping',(2.05,y,-.005),(3.14,.18,.12),m['stone'],.014)
        cube('Pool below-water end lining',(2.05,y,-.31),(3.14,.12,.5),m['stone'],.008)
    # Shallow entry steps remain visible through water.
    for i in range(3):
        cube('Pool submerged limestone entry tread',(2.05,2.4+i*.29,-.14-i*.09),(2.78,.29,.12),m['stone'],.009)


def courtyard_floor(m):
    rng=random.Random(18)
    pitch=1.0
    for i in range(13):
        for j in range(14):
            x=-6+i*pitch
            y=-6+j*pitch
            if .1<x<4 and 1.6<y<12:continue
            if (round(x),round(y)) in PLANTING_PIT:continue
            slab=cube('Courtyard honed limestone / 3mm construction joint',(x,y,-.10),(pitch-.003,pitch-.003,.18),m['floor'],.004)
            # Tiny edge variation; avoid a perfectly repeated synthetic grid.
            slab.location.z+=rng.uniform(-.0005,.0005)
    # The courtyard olive grows from a real pit: soil, gravel mulch and a flush bronze angle.
    cube('Olive planting pit / soil',(-3.5,2.0,-.115),(1.994,.994,.15),m['soil'],.004)
    pebble_patch('Olive planting pit / pale gravel mulch',(-3.5,2.0,-.052),1.9,.9,m['stone'],seed=88,count=420)
    for x in [-4.5,-2.5]:
        cube('Planting pit bronze edge angle',(x,2.0,-.035),(.012,1.0,.05),m['brass'],.002)
    for y in [1.5,2.5]:
        cube('Planting pit bronze edge angle',(-3.5,y,-.035),(2.012,.012,.05),m['brass'],.002)
    cube('Loggia front foundation',(0,-6.9,-.2),(14,1.8,.4),m['concrete'],.015)
    for i in range(4):
        cube('Garden transition grounded limestone tread',(-1.35,7.35+i*.74,-.03),(2.1,.63,.20),m['stone'],.014)
    poly_curve('Foreground fine drainage slot',[(-5.7,-3.8,.001),(-.15,-3.8,.001)],.006,m['ink'])


def architecture(m):
    # Two genuine cast walls frame a generous rear garden opening.
    wall_a=curved_wall('East curved cast-concrete wing',5.65,.045*math.pi,.34*math.pi,3.9,.28,m['concrete'])
    wall_b=curved_wall('West curved cast-concrete wing',5.65,.69*math.pi,1.20*math.pi,3.9,.28,m['concrete'])
    physical_uv(wall_a)
    physical_uv(wall_b)
    # Extend a quiet plaster volume to the camera: photograph a room, never a freestanding model.
    cube('Western inhabited plaster return',(-5.35,-3.5,2.02),(.34,9.0,4.04),m['plaster'],.025)
    cube('West inset skirting shadow reveal',(-5.17,-3.3,.07),(.022,8.7,.026),m['ink'],.003)
    roof=annulus('Concrete oculus canopy / real aperture',2.64,6.02,.26,m['concrete'],4.01)
    physical_uv(roof)
    # Actual bronze inner reveal separates skylight edge and soffit.
    physical_uv(annulus('Oculus slender bronze drip edge',2.62,2.655,.028,m['brass'],3.88))
    cube('Deep entrance loggia ceiling outside camera',(0,-5.2,4.0),(12.1,5.1,.29),m['plaster'],.026)
    cube('Garden opening concrete header',(0,5.08,3.73),(5.9,.32,.38),m['concrete'],.024)
    for x in [-2.91,2.91]:
        cube('Garden opening limestone jamb',(x,5.09,1.85),(.17,.38,3.7),m['stone'],.012)
    cube('Garden opening recessed bronze track',(0,5.08,.012),(5.8,.052,.028),m['brass'],.006)
    # A slid-open glass leaf remains nested against the east wing.
    cube('Sliding leaf / clear glazing',(3.05,4.99,1.81),(1.55,.014,3.4),m['glass'],.004)
    for x in [2.28,3.82]:
        cube('Sliding leaf / satin bronze upright',(x,4.99,1.82),(.021,.035,3.45),m['brass'],.004)
    for z in [.10,3.54]:
        cube('Sliding leaf / satin bronze horizontal',(3.05,4.99,z),(1.57,.035,.021),m['brass'],.004)
    for x,y in [(-4.35,-2.95),(4.35,-2.95)]:
        cylinder('Slim load-bearing bronze column',(x,y,1.93),.059,3.86,m['brass'],64,.006)
        cylinder('Column recessed base shoe',(x,y,.035),.078,.05,m['metal'],64,.006)
    # Concrete horizontal pour joint, pale enough to stay architectural.
    for start,end in [(.045*math.pi,.34*math.pi),(.69*math.pi,1.20*math.pi)]:
        points=[(math.cos(start+(end-start)*i/64)*5.646,math.sin(start+(end-start)*i/64)*5.646,1.36) for i in range(65)]
        poly_curve('Curved concrete 4mm construction seam',points,.003,m['stone'])
    # Soffit has restrained expansion joints, not an artificially featureless plate.
    for x in [-3.1,-1.7,1.7,3.1]:
        poly_curve('Loggia soffit recessed joint',[(x,-7.5,3.847),(x,-3.0,3.847)],.0025,m['ink'])
    # External timber shade system casts fine and varying actual contact shadows.
    for i in range(15):
        beam=cube('Garden pergola oak blade',(-4.9+i*.28,6.25,4.23),(.064,3.35,.12),m['oak'],.009)
        beam.rotation_euler.z=.018
    for x in [-5.02,-.85]:
        cube('Garden pergola slim side beam',(x,6.25,4.15),(.11,3.55,.13),m['oak'],.011)


def rounded_equator(hx,hy,radius,offset,step=.01):
    """Cyclic mid-height outline of a bevelled box, offset outward for a sewn welt."""
    r=radius+offset;ix,iy=hx-radius,hy-radius;points=[]
    corners=((ix,-iy),(ix,iy),(-ix,iy),(-ix,-iy))
    for i,(cx,cy) in enumerate(corners):
        start=-math.pi/2+i*math.pi/2
        points.extend((cx+r*math.cos(start+k*math.pi/32),cy+r*math.sin(start+k*math.pi/32),0.0) for k in range(17))
        nx,ny=corners[(i+1)%4]
        end=(cx+r*math.cos(start+math.pi/2),cy+r*math.sin(start+math.pi/2))
        nxt=(nx+r*math.cos(start+math.pi/2),ny+r*math.sin(start+math.pi/2))
        n=max(1,round(math.dist(end,nxt)/step))
        points.extend((end[0]+(nxt[0]-end[0])*t/n,end[1]+(nxt[1]-end[1])*t/n,0.0) for t in range(1,n))
    return points


def furniture(m):
    # Slatted oak built-in seat follows the left side of the courtyard, full-size.
    x0,y0=-3.04,.63
    rounded_box('Oak bench concealed frame',(x0,y0,.43),(3.55,.78,.12),m['oak'],.035)
    for i in range(13):
        rounded_box('Oak seat slat / longitudinal relief ridge',(x0,y0-.35+i*.058,.515),(3.6,.048,.055),m['oak'],.012)
    for x in [-4.42,-1.66]:
        rounded_box('Bench monolithic oak support',(x,y0,.23),(.12,.65,.42),m['oak'],.025)
        cube('Bench inset dark foot',(x,y0,.025),(.10,.57,.024),m['ink'],.006)
    # One casually composed linen pad with double stitched piping.
    cushion=rounded_box('Bench tailored linen seat cushion',(-3.31,.68,.64),(1.17,.62,.16),m['linen'],.065)
    cushion.rotation_euler.z=.035
    # The welt rides the pad's own rounded equator in its rotated frame. Lightly
    # embedded, it stays under the settled throw (>=5mm clearance) instead of
    # bowing out across the faces as the former five-point loop did.
    welt=poly_curve('Cushion linen welt / sewn perimeter',rounded_equator(.585,.31,.065,.0005),.0017,m['linen'])
    welt.data.splines[0].use_cyclic_u=True
    welt.data.resolution_u=2
    welt.parent=cushion
    pillow=rounded_box('Loosely resting linen lumbar cushion',(-3.40,.97,.91),(.76,.19,.48),m['linen'],.07)
    pillow.rotation_euler.x=-.18
    pillow.rotation_euler.z=-.10
    baked_cloth('solaris',m['linen'],'Oak bench linen throw / actual simulated drape')
    # Stone table: distinct base/top, softened real edge, restrained underside shadow gap.
    cylinder('Living stone table / carved pedestal',(-1.15,-.64,.255),.30,.51,m['stone'],128,.024)
    table=cylinder('Living stone table / honed oval top',(-1.15,-.64,.56),.78,.10,m['stone'],160,.02)
    table.scale.y=.76
    physical_uv(lathe_vessel('Hand thrown ceramic vase / open lipped hollow body',(-1.05,-.80,.612),m['clay']))
    cylinder('Quiet ceramic saucer',(-.91,-.91,.628),.14,.025,m['stone'],96,.008)
    # Small actual olive sprig: physical branching and curved blade leaves.
    branch('Vase slender olive twig',(-1.05,-.80,.98),(-1.11,-.76,1.40),.004,m['walnut'],end_radius=.0018)
    branch('Vase fine olive lateral',(-1.09,-.78,1.20),(-1.30,-.77,1.38),.0025,m['walnut'],end_radius=.001)
    verts=[]
    faces=[]
    for i in range(11):
        px=-1.09+(i%2-.5)*.12
        py=-.78+(i%3-.8)*.035
        pz=1.11+i*.025
        start=len(verts)
        verts.extend([(px-.07,py,pz),(px,py-.013,pz+.012),(px+.07,py,pz+.02),(px,py+.013,pz+.012)])
        faces.append((start,start+1,start+2,start+3))
    aggregate('Tabletop olive leaves',verts,faces,m['leaf'],True)
    cube('Small linen-covered architecture folio',(-1.00,-.54,.633),(.29,.22,.032),m['linen'],.004)
    cube('Folio fine paper edge',(-1.00,-.54,.649),(.278,.21,.006),m['plaster'],.001)
    # A full-scale lounge chair gives the view the familiar dimensions of habitation.
    chair_x,chair_y=-4.05,-2.12
    for x in [chair_x-.35,chair_x+.35]:
        for y in [chair_y-.29,chair_y+.29]:
            branch('Lounge chair oak leg',(x,y,.02),(x,y,.44),.029,m['oak'],end_radius=.024)
        branch('Lounge chair oak arm',(x,chair_y-.34,.66),(x,chair_y+.33,.66),.027,m['oak'])
    rounded_box('Lounge chair linen seat',(chair_x,chair_y,.47),(.76,.73,.15),m['linen'],.068)
    back=rounded_box('Lounge chair linen back',(chair_x,chair_y+.27,.86),(.74,.16,.68),m['linen'],.065)
    back.rotation_euler.x=-.15


# Mediterranean planting. Deliberately scene-local: the checkpoint renderer fingerprints
# world_common.py for every scene, so improving the shared tree would discard AUREL's
# completed, reviewed master. STRATA carries an identical copy for the same reason.
OLIVE_LEAVES = (('Olive leaf / grey-green upper', (.066, .082, .036)),
                ('Olive leaf / silvered underside', (.15, .165, .118)),
                ('Olive leaf / shaded inner leaf', (.036, .05, .02)),
                ('Olive leaf / young sunlit growth', (.098, .125, .044)))
OLIVE_WEIGHTS = (5, 2, 3, 1)
CYPRESS_LEAVES = (('Cypress scale foliage / deep green', (.016, .036, .015)),
                  ('Cypress scale foliage / lit sprays', (.036, .064, .024)))
CYPRESS_WEIGHTS = (3, 1)
SHRUBS = {
    'pittosporum': ((('Clipped pittosporum / glossy green', (.042, .075, .026)),
                     ('Clipped pittosporum / new growth', (.075, .11, .035))), (4, 1), .05, .022),
    'santolina': ((('Santolina mound / grey-green', (.11, .125, .08)),
                   ('Santolina mound / shaded', (.06, .07, .045))), (3, 2), .036, .014),
    'rosemary': ((('Rosemary / dark needle green', (.035, .055, .028)),
                  ('Rosemary / silvered needle', (.09, .105, .075))), (3, 1), .045, .009),
}


def foliage_object(name, buffers, palette):
    verts, faces, indices = buffers
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    # Leaf shaders ignore UVs; a placeholder layer spares the renderer's per-loop projection.
    mesh.uv_layers.new(name='Leaf / unused')
    for label, colour in palette:
        mesh.materials.append(leaf_material(label, colour))
    mesh.polygons.foreach_set('material_index', indices)
    mesh.polygons.foreach_set('use_smooth', [True] * len(faces))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj['leaves'] = len(faces) // 4
    return obj


def leaf_shell(rng, buffers, centre, radii, count, length, width, weights, lift=.55, keep=None):
    """Leaves through an ellipsoid clump, densest towards its surface, facing outwards and upwards."""
    verts, faces, indices = buffers
    choices = range(len(weights))
    for _ in range(count):
        z = rng.uniform(-1, 1)
        a = rng.uniform(0, math.tau)
        s = math.sqrt(max(0., 1 - z * z))
        d = Vector((s * math.cos(a), s * math.sin(a), z))
        r = 1 - .62 * rng.random() ** 1.6
        p = Vector((centre[0] + d.x * radii[0] * r, centre[1] + d.y * radii[1] * r,
                    centre[2] + d.z * radii[2] * r))
        if keep and not keep(p):
            continue
        n = Vector((d.x + rng.uniform(-.5, .5), d.y + rng.uniform(-.5, .5),
                    d.z + rng.uniform(.05, lift + .25)))
        n.normalize()
        t = n.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))))
        u = (t if t.length > 1e-5 else n.orthogonal()).normalized()
        v = n.cross(u)
        leaf = length * rng.uniform(.72, 1.28)
        half = width * rng.uniform(.4, .6)
        k = len(verts)
        verts.extend((p - u * (leaf * .45), p + v * half - u * (leaf * .1),
                      p + u * (leaf * .55) - n * (leaf * .08), p - v * half - u * (leaf * .1),
                      p + n * (leaf * .035)))
        faces.extend(((k + 4, k, k + 1), (k + 4, k + 1, k + 2),
                      (k + 4, k + 2, k + 3), (k + 4, k + 3, k)))
        shade = rng.choices(choices, weights=weights)[0]
        indices.extend((shade, shade, shade, shade))


def shell_count(radius, length, width, density, coverage=.25):
    return max(24, int(density * coverage * 4 * math.pi * radius * radius / (.5 * length * width)))


def tube(name, points, radii, mat, sides=14):
    """One continuous swept limb: no internal caps, kinks or bark seams between segments."""
    count = len(points)
    tangents = [(points[min(count - 1, k + 1)] - points[max(0, k - 1)]).normalized() for k in range(count)]
    reference = Vector((0, 0, 1)) if abs(tangents[0].z) < .9 else Vector((1, 0, 0))
    normal = tangents[0].cross(reference).normalized()
    verts, faces, along = [], [], [0.]
    for k in range(count):
        tangent = tangents[k]
        normal = (normal - tangent * normal.dot(tangent)).normalized()  # parallel transport
        binormal = tangent.cross(normal)
        if k:
            along.append(along[-1] + (points[k] - points[k - 1]).length)
        for i in range(sides):
            a = i / sides * math.tau
            verts.append(points[k] + (normal * math.cos(a) + binormal * math.sin(a)) * radii[k])
    for k in range(count - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((k * sides + i, k * sides + j, (k + 1) * sides + j, (k + 1) * sides + i))
    faces.append(tuple(range(sides - 1, -1, -1)))
    faces.append(tuple((count - 1) * sides + i for i in range(sides)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    layer = mesh.uv_layers.new(name='Bark / around and along limb in metres')
    for poly in mesh.polygons:
        poly.use_smooth = len(poly.vertices) == 4
        wrap = len(poly.vertices) == 4 and poly.vertices[0] % sides == sides - 1
        for loop in poly.loop_indices:
            index = mesh.loops[loop].vertex_index
            ring, step = divmod(index, sides)
            if wrap and step == 0:
                step = sides
            layer.data[loop].uv = (step / sides * math.tau * radii[ring], along[ring])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    return obj


def olive_bark(name):
    """Fissured grey bark: Voronoi plates stretched along each swept limb's length."""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = .9
    coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (9, 2.6, 1)
    links.new(coord.outputs['UV'], mapping.inputs['Vector'])
    warp = nodes.new('ShaderNodeTexNoise')
    warp.inputs['Scale'].default_value = 3
    warp.inputs['Detail'].default_value = 3
    links.new(mapping.outputs['Vector'], warp.inputs['Vector'])
    offset = nodes.new('ShaderNodeVectorMath')
    offset.operation = 'MULTIPLY_ADD'
    offset.inputs[1].default_value = (.35, .35, .35)
    links.new(warp.outputs['Color'], offset.inputs[0])
    links.new(mapping.outputs['Vector'], offset.inputs[2])
    plates = nodes.new('ShaderNodeTexVoronoi')
    plates.feature = 'DISTANCE_TO_EDGE'
    plates.inputs['Scale'].default_value = 7.5
    links.new(offset.outputs['Vector'], plates.inputs['Vector'])
    colour = nodes.new('ShaderNodeValToRGB')
    colour.color_ramp.elements[0].position = .0
    colour.color_ramp.elements[0].color = (.018, .016, .013, 1)
    colour.color_ramp.elements[1].position = .06
    colour.color_ramp.elements[1].color = (.115, .108, .09, 1)
    links.new(plates.outputs['Distance'], colour.inputs['Fac'])
    links.new(colour.outputs['Color'], shader.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .55
    bump.inputs['Distance'].default_value = .006
    links.new(plates.outputs['Distance'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return mat


def olive_tree(name, pos, height=4.5, seed=1, stems=1, density=1.0, heading=None, clip=None):
    """Gnarled olive: sinuous trunk, a few spreading primary limbs and a broad clumped crown."""
    rng = random.Random(seed)
    h = height
    bark = olive_bark('Olive / fissured grey bark')
    origin = Vector(pos)
    buffers = ([], [], [])
    leaf_len = .085 * max(.75, min(h / 5, 1.2))
    leaf_w = leaf_len * .24

    def limb(label, a, b, r0, r1):
        a = a - (b - a).normalized() * (r0 * .8)  # overlap conceals each joint
        branch(label, a, b, r0, bark, r1)

    def chain(label, points, radii):
        tube(label, points, radii, bark, 16 if radii[0] > .05 else 10)

    def curve(a, a_handle, b_handle, b, count):
        return list(interpolate_bezier(a, a_handle, b_handle, b, count))

    # One broad dome envelope shared by every stem; clumps overlap into a single canopy.
    crown_base = h * rng.uniform(.36, .44)
    half_w = h * rng.uniform(.34, .42)
    half_h = (h - crown_base) * .5
    crown = origin + Vector((rng.uniform(-.04, .04) * h, rng.uniform(-.04, .04) * h, crown_base + half_h))

    def outer_leaf(p):
        if clip and not clip(p):
            return False
        q = p - crown
        e = (q.x / half_w) ** 2 + (q.y / half_w) ** 2 + (q.z / half_h) ** 2
        return e > .38 or rng.random() < .16  # shaded interiors keep only sparse leaves

    anchors = []  # (point, radius) along every trunk head and primary limb
    ang0 = rng.uniform(0, math.tau) if heading is None else heading
    r0 = h * (.042 if stems == 1 else .03)
    rise = crown_base + h * .02
    for s in range(stems):
        stem_heading = ang0 + s * math.tau / stems
        outward = Vector((math.cos(stem_heading), math.sin(stem_heading), 0))
        spread = (.12 if stems > 1 else .04) * h
        base = origin + outward * (r0 * .55 if stems > 1 else 0)
        head = origin + outward * spread + Vector((rng.uniform(-.02, .02) * h, rng.uniform(-.02, .02) * h, rise))

        def sway():
            return Vector((rng.uniform(-.045, .045) * h, rng.uniform(-.045, .045) * h, 0))
        points = curve(base, base + Vector((0, 0, rise * .38)) + sway(),
                       head - Vector((0, 0, rise * .32)) + sway(), head, 9)
        radii = [r0 * (1.14 - .5 * k / 8) * rng.uniform(.95, 1.05) for k in range(9)]
        head_r = radii[-1]
        # A short tapered crown closes the trunk inside the emerging limbs.
        points.append(head + (head - points[-2]).normalized() * (head_r * 1.4))
        radii.append(head_r * .45)
        chain(f'{name} / gnarled trunk {s}', points, radii)
        head = points[-3]
        anchors.extend(zip(points[5:-1], radii[5:-1]))
        primaries = rng.randint(3, 5) if stems == 1 else rng.randint(2, 3)
        for i in range(primaries):
            if stems == 1:
                az = stem_heading + (i + rng.uniform(-.3, .3)) * math.tau / primaries
            else:
                az = stem_heading + rng.uniform(-1.05, 1.05)  # each stem keeps to its own side
            direction = Vector((math.cos(az), math.sin(az), 0))
            reach = half_w * rng.uniform(.62, .86)
            lift = half_h * rng.uniform(.85, 1.35)
            tip = Vector((crown.x, crown.y, head.z)) + direction * reach + Vector((0, 0, lift))
            limb_points = curve(head, head + direction * (reach * .25) + Vector((0, 0, lift * .45)),
                                tip - direction * (reach * .3) + Vector((rng.uniform(-.1, .1) * h,
                                                                         rng.uniform(-.1, .1) * h, 0)), tip, 6)
            limb_radii = [head_r * .76 * (1 - .74 * k / 5) for k in range(6)]
            chain(f'{name} / primary limb {s}-{i}', limb_points, limb_radii)
            anchors.extend(zip(limb_points[1:], limb_radii[1:]))
    for i in range(int(13 + 2.2 * h)):
        # Clump centres sit in the outer part of the dome, more above than below.
        az = ang0 + i * 2.39996 + rng.uniform(-.25, .25)
        z = rng.uniform(-.55, 1.0)
        reach = rng.uniform(.5, .82)
        horizontal = math.sqrt(max(0., 1 - z * z))
        centre = crown + Vector((math.cos(az) * horizontal * half_w * reach,
                                 math.sin(az) * horizontal * half_w * reach, z * half_h * reach))
        start, radius = min(anchors, key=lambda anchor: (anchor[0] - centre).length)
        bend = start.lerp(centre, .5) + Vector((0, 0, rng.uniform(.02, .07) * h))
        twig = max(.006, radius * .45)
        limb(f'{name} / leafy branch {i}', start, bend, twig, twig * .7)
        limb(f'{name} / leafy branch tip {i}', bend, centre, twig * .7, twig * .25)
        sub = h * rng.uniform(.105, .16)
        leaf_shell(rng, buffers, centre, (sub, sub, sub * .8),
                   shell_count(sub, leaf_len, leaf_w, density, .2), leaf_len, leaf_w, OLIVE_WEIGHTS,
                   keep=outer_leaf)
    return foliage_object(name + ' / clumped olive canopy', buffers, OLIVE_LEAVES)


def cypress(name, pos, height=8.0, seed=1, density=1.0):
    """Mediterranean cypress: a narrow, slightly irregular column of dense sprays."""
    rng = random.Random(seed)
    origin = Vector(pos)
    bark = material(name + ' / cypress bark', (.05, .035, .022), (.15, .10, .06), .9, (20, 20, .6), grain=True)
    branch(name + ' / trunk', origin, origin + Vector((0, 0, height * .9)), height * .016, bark, height * .004)
    buffers = ([], [], [])
    leaf_len, leaf_w = .07, .028
    radius = height * rng.uniform(.078, .094)
    levels = max(6, int(height / .4))
    for i in range(levels):
        t = (i + .5) / levels
        # Columnar: slightly narrow at the foot, fullest near a third, tapering to a point.
        r = radius * max(.12, (1 - t ** 2.2) ** .7) * (.8 + .2 * min(1, t / .22))
        r *= .93 + .14 * math.sin(t * 11 + seed)
        for _ in range(2):
            centre = origin + Vector((rng.uniform(-.2, .2) * r, rng.uniform(-.2, .2) * r,
                                      height * (.04 + .94 * t)))
            leaf_shell(rng, buffers, centre, (r, r, max(r, height / levels) * 1.05),
                       shell_count(r, leaf_len, leaf_w, density, .24), leaf_len, leaf_w, CYPRESS_WEIGHTS, lift=.25)
    return foliage_object(name + ' / dense cypress column', buffers, CYPRESS_LEAVES)


def shrub(name, pos, radius=.5, height=.6, seed=1, kind='pittosporum', density=1.0):
    """Low irregular mound of overlapping leaf clumps resting on its planting bed."""
    rng = random.Random(seed)
    palette, weights, leaf_len, leaf_w = SHRUBS[kind]
    origin = Vector(pos)
    buffers = ([], [], [])
    for _ in range(rng.randint(4, 6)):
        offset = Vector((rng.uniform(-.55, .55) * radius, rng.uniform(-.55, .55) * radius, 0))
        r = radius * rng.uniform(.42, .72)
        top = height * rng.uniform(.62, 1.0)
        centre = origin + offset + Vector((0, 0, top * .5))
        leaf_shell(rng, buffers, centre, (r, r * rng.uniform(.8, 1.1), top * .52),
                   shell_count(r, leaf_len, leaf_w, density, .42), leaf_len, leaf_w, weights, lift=.7)
    return foliage_object(name, buffers, palette)


def garden(m):
    garden_ground=material('Dry garden / warm fine gravel',(.18,.145,.095),(.34,.285,.20),.93,(3,3,3))
    # Continuous garden substrate supports paths without filling the pool basin.
    # Planting grade meets the coping; no exposed floating slabs or dark cutouts.
    cube('Garden deep continuous substrate',(0,65,-1.0),(120,170,.70),garden_ground,.015)
    # Side strips meet the rear grade at y=11.5; coplanar overlapping opaque
    # volumes create black ray artifacts, even when their surfaces share a shader.
    cube('Garden west continuous planted grade',(-14.825,7.75,-.25),(30.35,7.5,.45),garden_ground,.018)
    cube('Garden east continuous planted grade',(18.875,7.75,-.25),(30.35,7.5,.45),garden_ground,.018)
    cube('Garden rear continuous planted grade',(0,65.75,-.25),(120,108.5,.45),garden_ground,.018)
    cube('Garden path continuous compacted foundation',(-1.35,14.5,-.20),(2.32,17.5,.32),garden_ground,.009)
    # Contrasting garden paths and masonry bounding the planted beds.
    for i in range(10):
        cube('Garden limestone path',(-1.35,10.4+i*1.2,-.06),(2.1,1.07,.14),m['stone'],.017)
    for y in [9.8,14.5]:
        cube('Raised planting terrace retaining edge',(-4.6,y,.05),(5.1,.23,.38),m['stone'],.021)
    pebble_patch('Dry garden ground / pale limestone gravel',(-4.5,9.0,.015),5,3,m['stone'],seed=61,count=370)
    pebble_patch('Pool garden margin / fine aggregate',(5.1,9.0,.01),2.6,5,m['floor'],seed=73,count=230)
    # Mature olives with cypress accents; every canopy is clumped leaf geometry on real limbs.
    def clear_of_courtyard_shell(p):
        # Curved wings' inner face is at r=5.51 m; the canopy soffit sits near 3.88 m.
        return math.hypot(p.x,p.y)<5.42 and p.z<3.7
    olive_tree('Courtyard olive / planted pit',(-3.85,1.95,-.04),height=3.35,seed=15,stems=2,
               heading=math.radians(100),clip=clear_of_courtyard_shell)
    for name,pos,height,seed in [('Garden olive west',(-6.2,12.2,0),5.0,51),
                                  ('Garden olive east',(6.0,13.8,0),4.5,72)]:
        olive_tree(name,pos,height=height,seed=seed)
    cypress('Garden axis cypress beyond the wall',(-1.3,24.5,0),height=8.6,seed=21)
    olive_tree('Distant east grove olive',(9.2,26.3,0),height=6.2,seed=35,density=.75)
    for i,(x,y,radius,height,kind) in enumerate([
            (-6.5,10.7,.55,.6,'pittosporum'),(-5.1,11.3,.45,.38,'santolina'),(-3.55,10.55,.5,.5,'rosemary'),
            (-3.0,12.7,.42,.36,'santolina'),(-4.7,13.4,.6,.62,'pittosporum'),(-6.7,13.7,.5,.45,'rosemary'),
            (4.65,8.6,.48,.5,'rosemary'),(6.95,9.35,.55,.6,'pittosporum'),(5.35,11.2,.42,.36,'santolina'),
            (7.25,12.05,.5,.5,'rosemary'),(4.75,16.5,.55,.58,'pittosporum'),(6.65,17.6,.45,.4,'santolina'),
            (-9.0,21.9,.6,.6,'pittosporum'),(-5.6,21.8,.5,.45,'rosemary'),(-3.4,22.0,.45,.4,'santolina'),
            (1.2,21.9,.55,.55,'pittosporum'),(4.5,21.9,.5,.45,'rosemary'),(8.2,21.95,.6,.6,'pittosporum'),
            (11.5,22.0,.45,.4,'santolina')]):
        shrub(f'Garden {kind} mound',(x,y,0),radius,height,seed=1200+i,kind=kind)
    rng=random.Random(604)
    # Small native planting appears as designed drifts, leaving water and path legible.
    for i in range(35):
        side=-1 if i<19 else 1
        x=rng.uniform(-7,-2.9) if side<0 else rng.uniform(4.0,7.8)
        y=rng.uniform(7.7,20)
        plant('Garden mixed Mediterranean planting',(x,y,0),size=rng.uniform(.35,.90),seed=300+i)
    # Courtyard grasses grow only inside the olive's planting pit, never from stone slabs.
    plant('Courtyard pit / soft grasses',(-4.25,1.72,-.04),size=.42,seed=96)
    plant('Courtyard pit / soft grasses',(-2.82,2.24,-.04),size=.38,seed=97)
    shrub('Courtyard pit / santolina underplanting',(-3.0,1.76,-.04),.3,.28,seed=98,kind='santolina')
    # Low boundary and a staggered grove provide a credible garden-scale horizon.
    # Root's daylight HDRI supplies the distant environment beyond this planted layer.
    cube('Garden low limewashed boundary wall',(0,23,.43),(48,.35,.86),m['plaster'],.025)
    for i,(x,y,h,kind) in enumerate([(-16,28,4.6,'olive'),(-11,31,8.8,'cypress'),(-6,29,4.3,'olive'),
                                     (3,32,9.2,'cypress'),(14,29,4.7,'olive'),(20,33,8.0,'cypress')]):
        if kind=='cypress':
            cypress('Beyond boundary / cypress',(x,y,-.025),height=h,seed=710+i,density=.8)
        else:
            olive_tree('Beyond boundary / mature olive',(x,y,-.025),height=h,seed=710+i,density=.7)
    for i in range(48):
        x=rng.uniform(-19,20)
        y=rng.uniform(20.8,27)
        plant('Boundary layered native shrub drift',(x,y,-.025),size=rng.uniform(.65,1.3),seed=820+i)
    for i in range(22):
        x=rng.uniform(-7.2,7.8)
        y=rng.uniform(11.8,19.5)
        if -2.65<x<-.10:continue
        plant('Rear pool lush planted transition',(x,y,-.025),size=rng.uniform(.5,1.05),seed=930+i)


def build(m, view='wide'):
    courtyard_floor(m)
    water_surface(m)
    architecture(m)
    furniture(m)
    garden(m)
    sun((-5,-8,18),(0,2,0),energy=2.3,color=(1,.93,.81),angle=.022)
    area('Skylight broad cool fill',(0,-2,6),(0,2,.8),energy=145,color=(.80,.89,1),size=6)
    area('Garden bounced warm light',(1,9,3),(0,1,1.2),energy=85,color=(1,.90,.73),size=4)
    if view=='detail':
        camera((.42,-3.28,1.13),(-2.16,.17,.80),lens=54,focus=(-1.60,-.30,.82),fstop=7.1)
    else:
        camera((3.35,-4.75,1.60),(-.85,3.8,1.80),lens=27,focus=(-.8,2.8,1.4),fstop=11)
    return {'world':'SOLARIS / oculus courtyard home and Mediterranean garden',
            'view':view,'units':'metres','originalGeometry':True,
            'description':'Inhabited loggia, constructed curved wings and oculus, slatted oak/linen furniture, ceramic tabletop still life, actual pool, continuous planted garden, low boundary and mature layered grove.'}
