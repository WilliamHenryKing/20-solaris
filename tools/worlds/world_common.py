"""Physical-scale modeling helpers and photographed CC0 PBR materials.
All architectural geometry is authored here/in each scene. Poly Haven material
maps and HDRI are attributed in the adjacent texture manifest, not claimed as original.
"""
import importlib.util
import json
import math
import random
from pathlib import Path
import bpy
import bmesh
from mathutils import Vector

BASE = Path(__file__).resolve().parent.parent / 'render-architecture-cuda.py'
spec = importlib.util.spec_from_file_location('original_geometry', BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
material = base.material
sun = base.sun
lathe_vessel = base.lathe_vessel

def area(*args,**kwargs):
    obj=base.area(*args,**kwargs)
    # Bounce cards must illuminate surfaces without becoming white rectangles
    # seen through the room's glazing or reflected in its water.
    obj.visible_camera=False
    obj.visible_glossy=False
    obj.visible_transmission=False
    return obj

def outward(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    bm.to_mesh(obj.data);bm.free();obj.data.update()

def uv_cylindrical(obj):
    mesh=obj.data
    layer=mesh.uv_layers.active or mesh.uv_layers.new(name='Continuous physical cylindrical metres')
    radius=max(math.hypot(v.co.x,v.co.y) for v in mesh.vertices)
    circumference=math.tau*radius
    for face in mesh.polygons:
        coords=[]
        for index in face.loop_indices:
            v=mesh.vertices[mesh.loops[index].vertex_index].co
            coords.append((math.atan2(v.y,v.x)*radius,v.z) if abs(face.normal.z)<.9 else (v.x,v.y))
        if abs(face.normal.z)<.9 and max(c[0] for c in coords)-min(c[0] for c in coords)>circumference*.5:
            coords=[(u+circumference if u<0 else u,v) for u,v in coords]
        for index,uv in zip(face.loop_indices,coords):layer.data[index].uv=uv
    obj['uv_kind']='cylindrical'

def annulus(*args,**kwargs):
    obj=base.annulus(*args,**kwargs);outward(obj);uv_cylindrical(obj);return obj

def curved_wall(*args,**kwargs):
    obj=base.curved_wall(*args,**kwargs);outward(obj);uv_cylindrical(obj);return obj

def uv_project(obj):
    mesh = obj.data
    layer = mesh.uv_layers.active or mesh.uv_layers.new(name='Physical metres')
    rng = random.Random(obj.name)
    offset = (rng.random()*7, rng.random()*9)
    for poly in mesh.polygons:
        axis = max(range(3), key=lambda i: abs(poly.normal[i]))
        for index in poly.loop_indices:
            co = mesh.vertices[mesh.loops[index].vertex_index].co
            uv = (co.y, co.z) if axis==0 else ((co.x, co.z) if axis==1 else (co.x, co.y))
            layer.data[index].uv = (uv[0]+offset[0], uv[1]+offset[1])

def cube(name, location, size, material, bevel=.01):
    x,y,z=(v/2 for v in size)
    verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.location=location;mesh.materials.append(material)
    if bevel:
        mod=obj.modifiers.new('True eased architectural edges','BEVEL')
        mod.width=bevel;mod.segments=4
    uv_project(obj)
    if bevel:
        obj.modifiers[-1].segments = 4
        mod = obj.modifiers.new('Area weighted architectural normals','WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return obj

def rounded_box(name, location, size, material, bevel=.08):
    obj=cube(name,location,size,material,bevel)
    # Broad rounded upholstery/stone edges need continuous shading. Flat source
    # polygons propagated into the bevel previously produced visible bands even
    # at the final sample count. Keep planar faces stable with the weighted
    # normals already supplied by cube(), and resolve the curved silhouette.
    for polygon in obj.data.polygons:
        polygon.use_smooth=True
    if bevel:
        obj.modifiers[0].segments=16
        obj.modifiers[0].harden_normals=True
    return obj

def cylinder(name, location, radius, depth, material, vertices=96, bevel=.015):
    points=[(radius*math.cos(i/vertices*math.tau),radius*math.sin(i/vertices*math.tau),z) for z in [-depth/2,depth/2] for i in range(vertices)]
    faces=[tuple(range(vertices-1,-1,-1)),tuple(range(vertices,vertices*2))]
    faces.extend((i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.location=location;mesh.materials.append(material)
    for face in mesh.polygons:face.use_smooth=len(face.vertices)==4
    if bevel:
        mod=obj.modifiers.new('Soft cast edge','BEVEL');mod.width=bevel;mod.segments=4
    uv_cylindrical(obj)
    return obj

def camera(location,target,lens=32,focus=None,fstop=8):
    obj=base.camera(location,target,lens)
    obj.data.clip_end=1500
    obj.data.sensor_width=36
    if focus is not None:
        obj.data.dof.use_dof=True
        obj.data.dof.focus_distance=(Vector(focus)-obj.location).length
        obj.data.dof.aperture_fstop=fstop
        obj.data.dof.aperture_blades=9
    return obj

def poly_curve(name,points,radius,mat):
    data=bpy.data.curves.new(name,'CURVE')
    data.dimensions='3D'
    data.resolution_u=8
    data.bevel_depth=radius
    data.bevel_resolution=3
    spline=data.splines.new('BEZIER')
    spline.bezier_points.add(len(points)-1)
    for point,co in zip(spline.bezier_points,points):
        point.co=co
        point.handle_left_type='AUTO'
        point.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    return obj

def branch(name,a,b,radius,mat,end_radius=None):
    vec=Vector(b)-Vector(a)
    radius2=end_radius if end_radius is not None else radius*.45
    segments=12
    verts=[(math.cos(i/segments*math.tau)*r,math.sin(i/segments*math.tau)*r,z) for z,r in [(-vec.length/2,radius),(vec.length/2,radius2)] for i in range(segments)]
    faces=[tuple(range(segments-1,-1,-1)),tuple(range(segments,segments*2))]
    faces.extend((i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.location=(Vector(a)+Vector(b))*.5
    obj.rotation_euler=vec.to_track_quat('Z','Y').to_euler()
    mesh.materials.append(mat)
    for p in mesh.polygons:p.use_smooth=len(p.vertices)==4
    return obj

def pbr(name,root,asset,scale=1,tint=None,normal=.35,rough_range=(.3,.8),crop=None,linen=False):
    folder=Path(root)/asset
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    bsdf=nodes.get('Principled BSDF')
    coord=nodes.new('ShaderNodeTexCoord')
    mapping=nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value=(scale,scale,scale)
    links.new(coord.outputs['UV'],mapping.inputs['Vector'])
    vector=mapping.outputs[0]
    if crop:
        # Sample the actual mineral face within one photographed slab; its
        # mortar joints must never become fake seams across a carved monolith.
        sep=nodes.new('ShaderNodeSeparateXYZ');links.new(vector,sep.inputs[0])
        combined=nodes.new('ShaderNodeCombineXYZ')
        for i in range(2):
            ping=nodes.new('ShaderNodeMath');ping.operation='PINGPONG';ping.inputs[1].default_value=1
            links.new(sep.outputs[i],ping.inputs[0])
            span=nodes.new('ShaderNodeMath');span.operation='MULTIPLY_ADD'
            span.inputs[1].default_value=crop[i+2]-crop[i]
            span.inputs[2].default_value=crop[i]
            links.new(ping.outputs[0],span.inputs[0]);links.new(span.outputs[0],combined.inputs[i])
        vector=combined.outputs[0]
    def texture(kind):
        matches=list(folder.glob(f'*{kind}*2k.jpg'))
        if not matches: return None
        node=nodes.new('ShaderNodeTexImage')
        node.image=bpy.data.images.load(str(matches[0]),check_existing=True)
        if kind not in ['diff','col']:node.image.colorspace_settings.name='Non-Color'
        links.new(vector,node.inputs['Vector'])
        return node
    color=texture('diff') or texture('col')
    if not color:raise FileNotFoundError(f'Missing required color map for {asset}')
    if color:
        source=color.outputs['Color']
        if linen:
            grey=nodes.new('ShaderNodeRGBToBW');links.new(source,grey.inputs[0])
            ramp=nodes.new('ShaderNodeValToRGB')
            ramp.color_ramp.elements[0].position=0
            ramp.color_ramp.elements[0].color=(.36,.32,.25,1)
            ramp.color_ramp.elements[1].position=.24
            ramp.color_ramp.elements[1].color=(.86,.79,.65,1)
            links.new(grey.outputs[0],ramp.inputs[0]);source=ramp.outputs[0]
        if tint:
            mix=nodes.new('ShaderNodeMixRGB')
            mix.blend_type='MULTIPLY'
            mix.inputs[0].default_value=1
            mix.inputs[2].default_value=(*tint,1)
            links.new(source,mix.inputs[1])
            source=mix.outputs[0]
        links.new(source,bsdf.inputs['Base Color'])
    rough=texture('rough')
    if not rough:raise FileNotFoundError(f'Missing required roughness map for {asset}')
    if rough:
        mapping_r=nodes.new('ShaderNodeMapRange')
        mapping_r.inputs['To Min'].default_value=rough_range[0]
        mapping_r.inputs['To Max'].default_value=rough_range[1]
        links.new(rough.outputs['Color'],mapping_r.inputs['Value'])
        links.new(mapping_r.outputs[0],bsdf.inputs['Roughness'])
    normal_tex=texture('nor_gl')
    if not normal_tex:raise FileNotFoundError(f'Missing required normal map for {asset}')
    if normal_tex:
        n=nodes.new('ShaderNodeNormalMap')
        n.inputs['Strength'].default_value=normal
        links.new(normal_tex.outputs['Color'],n.inputs['Color'])
        links.new(n.outputs[0],bsdf.inputs['Normal'])
    return mat

def palette(root):
    mats=base.palette()
    mats['walnut']=pbr('Walnut / photographed grain, oil finish',root,'rosewood_veneer1',.55,(.32,.37,.37),.3,(.28,.5))
    mats['oak']=pbr('Oak / photographed close grain',root,'fine_grained_wood',.7,(.86,.80,.65),.4,(.32,.6))
    mats['stone']=pbr('Honed vein stone / photographed mineral surface',root,'marble_01',.34,(.95,.91,.83),.2,(.33,.55),crop=(.40,.49,.93,.73))
    mats['floor']=pbr('Warm limestone finish / fine textured concrete',root,'concrete_wall_004',.32,(1,.98,.92),.22,(.5,.78),crop=(.36,.69,.70,.84))
    mats['concrete']=pbr('Cast concrete / photographed mineral pores',root,'concrete_wall_004',.6,(.95,.96,.93),.4,(.57,.88),crop=(.36,.69,.70,.84))
    mats['plaster']=pbr('Lime plaster / photographed trowel texture',root,'plastered_wall',.45,(1,.97,.86),.18,(.64,.88))
    mats['clay']=pbr('Clay / real plaster relief in earth pigment',root,'plastered_wall',.6,(.51,.22,.13),.25,(.64,.85))
    mats['linen']=pbr('Natural linen / real woven fibres',root,'rough_linen',3.5,None,.5,(.8,1),linen=True)
    mats['linen'].node_tree.nodes.get('Principled BSDF').inputs['Sheen Weight'].default_value=.25
    mats['soil']=material('Earth / ground humus',(.035,.026,.014),(.09,.07,.03),.96,(9,9,9))
    glass=bpy.data.materials.new('Low iron architectural glazing')
    glass.use_nodes=True
    p=glass.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(.94,.98,.97,1)
    p.inputs['Transmission Weight'].default_value=1
    p.inputs['Roughness'].default_value=.012
    p.inputs['IOR'].default_value=1.45
    # Architectural glazing: straight-through shadow transport avoids making
    # an otherwise clear window opaque to direct light when caustics are off.
    # Camera/reflection/refraction rays still use the physical glass BSDF.
    path=glass.node_tree.nodes.new('ShaderNodeLightPath')
    transparent=glass.node_tree.nodes.new('ShaderNodeBsdfTransparent')
    transparent.inputs[0].default_value=(.94,.97,.95,1)
    mix=glass.node_tree.nodes.new('ShaderNodeMixShader')
    glass.node_tree.links.new(path.outputs['Is Shadow Ray'],mix.inputs[0])
    glass.node_tree.links.new(p.outputs[0],mix.inputs[1])
    glass.node_tree.links.new(transparent.outputs[0],mix.inputs[2])
    glass.node_tree.links.new(mix.outputs[0],glass.node_tree.nodes.get('Material Output').inputs[0])
    mats['glass']=glass
    water=glass.copy()
    water.name='Quiet reflection pool / subtle water movement'
    p=water.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(.72,.9,.83,1)
    p.inputs['IOR'].default_value=1.333
    p.inputs['Roughness'].default_value=.045
    noise=water.node_tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=7
    noise.inputs['Detail'].default_value=2
    bump=water.node_tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.25
    bump.inputs['Distance'].default_value=.003
    water.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height'])
    water.node_tree.links.new(bump.outputs[0],p.inputs['Normal'])
    mats['water']=water
    mats['leaf']=leaf_material('Living foliage',(.085,.14,.025))
    return mats

def leaf_material(name,color):
    mat=bpy.data.materials.get(name)
    if mat:return mat
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links
    p=n.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=.52
    p.inputs['Subsurface Weight'].default_value=.035
    p.inputs['Subsurface Radius'].default_value=(.25,.5,.1)
    trans=n.new('ShaderNodeBsdfTranslucent')
    trans.inputs[0].default_value=(*color,1)
    mix=n.new('ShaderNodeMixShader')
    mix.inputs[0].default_value=.24
    l.new(p.outputs[0],mix.inputs[1]);l.new(trans.outputs[0],mix.inputs[2])
    l.new(mix.outputs[0],n.get('Material Output').inputs[0])
    return mat

def tree(name,pos,height=4,seed=1):
    rng=random.Random(seed)
    bark=material(name+' / fissured bark',(.055,.043,.027),(.14,.11,.065),.86,(28,28,.45),grain=True)
    foliage=[leaf_material('Leaf sage',(.11,.15,.045)),leaf_material('Leaf sun green',(.12,.22,.035)),leaf_material('Leaf deep green',(.032,.077,.014)),leaf_material('Leaf young green',(.16,.25,.052))]
    origin=Vector(pos)
    top=origin+Vector((height*.035,0,height*.67))
    branch(name+' / trunk',origin,top,height*.033,bark,height*.01)
    verts=[];faces=[];indices=[]
    for i in range(32):
        angle=i*2.399+rng.uniform(-.2,.2)
        start=origin.lerp(top,rng.uniform(.48,.98))
        end=start+Vector((math.cos(angle)*height*rng.uniform(.16,.35),math.sin(angle)*height*rng.uniform(.16,.35),height*rng.uniform(.12,.3)))
        branch(name+f' / branch {i}',start,end,height*.009,bark,height*.002)
        for j in range(6):
            t=rng.uniform(.28,1.1)
            twigstart=start.lerp(end,t)
            twig=twigstart+Vector((rng.uniform(-.12,.12)*height,rng.uniform(-.12,.12)*height,rng.uniform(.04,.16)*height))
            branch(name+' / fine twig',twigstart,twig,height*.0019,bark,height*.00035)
            for k in range(26):
                centre=twigstart.lerp(twig,rng.random())+Vector((rng.uniform(-.09,.09)*height,rng.uniform(-.09,.09)*height,rng.uniform(-.055,.07)*height))
                size=rng.uniform(.032,.065)*min(height/3,1.7)
                a=rng.uniform(0,math.tau)
                u=Vector((math.cos(a),math.sin(a),rng.uniform(-.8,.8))).normalized()*size
                v=Vector((-math.sin(a),math.cos(a),rng.uniform(-.6,.6))).normalized()*size*.34
                mid=Vector((0,0,size*.13))
                startindex=len(verts)
                verts.extend([centre-u,centre-v,centre+u,centre+v,centre+mid])
                faces.extend([(startindex+4,startindex+k,startindex+(k+1)%4) for k in range(4)])
                shade=rng.choices(range(4),weights=[3,4,2,1])[0]
                indices.extend([shade]*4)
    mesh=bpy.data.meshes.new(name+' / thousands of individually curved leaves')
    mesh.from_pydata(verts,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name+' / full foliage canopy',mesh)
    bpy.context.collection.objects.link(obj)
    for mat in foliage:mesh.materials.append(mat)
    for p,index in zip(mesh.polygons,indices):p.material_index=index;p.use_smooth=True
    return obj

def plant(name,pos,size=1,seed=1):
    rng=random.Random(seed)
    verts=[];faces=[]
    origin=Vector(pos)
    for i in range(85):
        a=rng.uniform(0,math.tau)
        length=rng.uniform(.35,.95)*size
        lean=rng.uniform(.2,.75)*size
        width=rng.uniform(.008,.022)*size
        start=origin+Vector((rng.uniform(-.12,.12)*size,rng.uniform(-.12,.12)*size,0))
        side=Vector((-math.sin(a),math.cos(a),0))*width
        idx=len(verts)
        for j in range(7):
            t=j/6
            p=start+Vector((math.cos(a)*lean*t*t,math.sin(a)*lean*t*t,length*math.sin(t*1.6)))
            verts.extend([p-side*(1-t),p+side*(1-t)])
        for j in range(6):faces.append((idx+2*j,idx+2*j+1,idx+2*j+3,idx+2*j+2))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(verts,[],faces);mesh.update()
    mesh.materials.append(leaf_material('Grasses / olive green',(.12,.16,.055)))
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:p.use_smooth=True
    return obj

def environment(root,rotation=0,strength=.45,asset='kloofendal_48d_partly_cloudy'):
    world=bpy.context.scene.world
    world.use_nodes=True
    n=world.node_tree.nodes;l=world.node_tree.links
    n.clear()
    env=n.new('ShaderNodeTexEnvironment')
    env.image=bpy.data.images.load(str(next((Path(root)/asset).glob('*.hdr'))),check_existing=True)
    coord=n.new('ShaderNodeTexCoord')
    mapping=n.new('ShaderNodeMapping')
    mapping.inputs['Rotation'].default_value[2]=rotation
    l.new(coord.outputs['Generated'],mapping.inputs[0]);l.new(mapping.outputs[0],env.inputs['Vector'])
    bg=n.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=strength
    l.new(env.outputs[0],bg.inputs[0])
    out=n.new('ShaderNodeOutputWorld');l.new(bg.outputs[0],out.inputs[0])


def baked_cloth(scene, fabric_material, name=None):
    """Load the actual settled Cloth surface; never substitute analytic folds.

    Root copies reviewed bake exports into tools/worlds/cloth for portable builds.
    Coordinates are already world-space; rest UVs are retained vertex-for-vertex.
    """
    source=Path(__file__).resolve().parent/'cloth'/f'{scene}.json'
    if not source.is_file():
        raise FileNotFoundError(f'Required simulated cloth export missing: {source}; bake and copy it before rendering')
    data=json.loads(source.read_text(encoding='utf-8'))
    verts=data['vertices'];faces=data['faces'];uvs=data['uvs']
    if data.get('schema')!=1 or data.get('scene')!=scene or len(verts)!=len(uvs):
        raise ValueError(f'Invalid cloth export schema or UV topology: {source}')
    if not data.get('metadata',{}).get('cacheBaked'):
        raise ValueError(f'Cloth export does not attest a completed bake: {source}')
    mesh=bpy.data.meshes.new(f'{scene} / settled cloth mesh')
    mesh.from_pydata(verts,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='Simulated cloth / rest fabric direction')
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            layer.data[li].uv=uvs[mesh.loops[li].vertex_index]
    obj=bpy.data.objects.new(name or f'{scene} / gravity-settled throw',mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(fabric_material)
    sub=obj.modifiers.new('Smooth fluid simulated cloth','SUBSURF')
    sub.levels=2;sub.render_levels=2
    solid=obj.modifiers.new('Thin woven fabric thickness','SOLIDIFY')
    solid.thickness=.0015;solid.offset=0
    obj['cloth_export']=str(source)
    obj['cloth_simulation_frame']=data['metadata'].get('frame',0)
    obj['cloth_physics']='Blender Cloth / gravity / self collision'
    # Keep the silhouette quiet: no synthetic repeated fringe or rigid seam tubes.
    # Ordered exported boundaries remain available for a later close-up hem pass.
    return obj
