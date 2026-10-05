"""Actual CPU Cloth bakes for authored architecture worlds; root queues execution.
Run Blender --background --python tools/bake-cloth.py -- --scene solaris --output output/cloth/solaris.json
No rendering. JSON vertices are evaluated world-space; UVs retain rest fabric direction.
"""
import argparse
import json
import math
from pathlib import Path
import random
import sys
import time
import bpy


def collision_box(name, location, size, bevel=.04, rotation=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj=bpy.context.object
    obj.name=name
    obj.scale=size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.rotation_euler=rotation
    mod=obj.modifiers.new('Soft collision corners','BEVEL')
    mod.width=bevel
    mod.segments=4
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.modifiers.new('Cloth collision','COLLISION')
    obj.collision.thickness_outer=.003
    obj.collision.thickness_inner=.002
    obj.collision.cloth_friction=8
    return obj


def proxies(scene):
    collision_box('Floor proxy',(0,0,-.08),(16,16,.16),.005)
    if scene=='aurel':
        collision_box('Sofa foundation',(.5,.21,.35),(3.16,1.12,.22),.09)
        for i,x in enumerate((-.48,.50,1.48)):
            collision_box('Seat cushion '+str(i),(x,.12,.535),(.967,.94,.20),.075)
            collision_box('Back cushion '+str(i),(x,.66,.815),(.99,.27,.70),.065,(math.radians(10),0,0))
        for x in (-1.08,2.08):
            collision_box('Sofa arm',(x,.17,.59),(.23,1.06,.66),.07)
        collision_box('Loose right pillow',(1.46,.46,.90),(.51,.21,.49),.065,(math.radians(13),math.radians(7),math.radians(9)))
        return dict(centre=(1.05,.35,1.36),width=1.42,length=1.58,angle=-.18,seed=421)
    if scene=='strata':
        collision_box('Limestone seat',(-2.20,-3.78,.483),(2.36,.64,.073),.014)
        for x in (-3.07,-1.32):collision_box('Bench support',(x,-3.78,.225),(.16,.52,.45),.01)
        collision_box('Loose bench cushion',(-2.60,-3.80,.562),(.85,.56,.096),.048)
        return dict(centre=(-2.52,-3.75,.94),width=1.18,length=1.12,angle=.12,seed=572)
    collision_box('Oak bench seat',(-3.04,.63,.51),(3.60,.78,.06),.014)
    for x in (-4.42,-1.66):collision_box('Oak bench support',(x,.63,.23),(.12,.65,.42),.025)
    collision_box('Linen seat pad',(-3.31,.68,.64),(1.17,.62,.16),.065,(0,0,.035))
    collision_box('Linen lumbar pillow',(-3.40,.97,.91),(.76,.19,.48),.07,(-.18,0,-.10))
    return dict(centre=(-3.18,.70,1.24),width=1.18,length=1.28,angle=-.16,seed=831)


def fabric(config):
    # Nonperiodic broad rest perturbations seed a casually tossed, skewed cloth.
    # They are initial conditions only: every exported fold comes from Cloth physics.
    rng=random.Random(config['seed'])
    bumps=[(rng.uniform(-.55,.55),rng.uniform(-.55,.55),rng.uniform(-.08,.11),rng.uniform(.18,.45)) for _ in range(11)]
    nx,ny=70,100
    verts=[];faces=[];uv=[]
    cx,cy,cz=config['centre'];a=config['angle']
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx
            x=(u-.5)*config['width'];y=(v-.5)*config['length']
            z=sum(h*math.exp(-((x-bx)**2+(y-by)**2)/spread**2) for bx,by,h,spread in bumps)
            x+=.075*(v-.5)+.018*(v-.5)**2
            verts.append((cx+x*math.cos(a)-y*math.sin(a),cy+x*math.sin(a)+y*math.cos(a),cz+z+.16*(v-.5)-.08*(u-.5)))
            uv.append((u,v))
    for j in range(ny):
        for i in range(nx):
            k=j*(nx+1)+i
            faces.append((k,k+1,k+nx+2,k+nx+1))
    mesh=bpy.data.meshes.new('Rest linen / 70 by 100 cells')
    mesh.from_pydata(verts,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='Rest fabric direction')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:layer.data[li].uv=uv[mesh.loops[li].vertex_index]
    obj=bpy.data.objects.new('Actual gravity-settled throw',mesh)
    bpy.context.collection.objects.link(obj)
    boundary=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    return obj,uv,boundary


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',choices=['solaris'],required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--frames',type=int,default=130)
    args=parser.parse_args(argv)
    if not 100<=args.frames<=200:parser.error('--frames must be between100 and200')
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.render.fps=24;scene.frame_start=1;scene.frame_end=args.frames
    scene.gravity=(0,0,-9.81)
    config=proxies(args.scene)
    proxy_friction=8 if args.scene=='aurel' else 20
    for collider in scene.objects:
        if collider.collision:collider.collision.cloth_friction=proxy_friction
    obj,uv,boundary=fabric(config)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    cloth=obj.modifiers.new('Actual unpinned wool-linen cloth','CLOTH')
    settings=cloth.settings
    settings.quality=10;settings.mass=.22
    settings.tension_stiffness=18;settings.compression_stiffness=18;settings.shear_stiffness=8
    settings.bending_stiffness=.12
    settings.tension_damping=8;settings.compression_damping=8;settings.shear_damping=8;settings.bending_damping=.5
    settings.air_damping=2
    collisions=cloth.collision_settings
    collisions.use_collision=True;collisions.collision_quality=8
    collisions.distance_min=.004;collisions.friction=8
    collisions.use_self_collision=True;collisions.self_distance_min=.004;collisions.self_friction=6
    cache=cloth.point_cache
    cache.frame_start=1;cache.frame_end=args.frames
    # Save first so disk-backed cache has a stable editable .blend home.
    blend=output.with_suffix('.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    cache.use_disk_cache=True
    started=time.time()
    with bpy.context.temp_override(scene=scene,object=obj,active_object=obj,point_cache=cache):
        result=bpy.ops.ptcache.bake(bake=True)
    if 'FINISHED' not in result or not cache.is_baked:raise RuntimeError('Cloth cache did not bake successfully')
    scene.frame_set(args.frames);bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    evaluated=obj.evaluated_get(depsgraph)
    mesh=evaluated.to_mesh()
    try:
        vertices=[list(evaluated.matrix_world@v.co) for v in mesh.vertices]
        if len(vertices)!=len(uv):raise RuntimeError('Unexpected evaluated topology; cannot preserve rest UVs')
        payload={'schema':1,'scene':args.scene,'vertices':vertices,'faces':[list(p.vertices) for p in mesh.polygons],
                 'uvs':uv,'boundaryIndices':boundary,'boundaryLoops':[boundary],
                 'metadata':{'method':'Blender Cloth gravity and self-collision; no analytic final fold surface',
                             'blender':bpy.app.version_string,'frame':scene.frame_current,'frames':args.frames,
                             'cacheBaked':cache.is_baked,'seconds':time.time()-started,'units':'metres',
                             'space':'world','restPose':config,'physics':{'quality':10,'collisionQuality':8,'mass':.22,
                             'tension':18,'compression':18,'shear':8,'bending':.12,'distance':.004,'selfDistance':.004,
                             'gravity':list(scene.gravity),'unpinned':True,'proxyFriction':proxy_friction},'blendFile':str(blend)}}
        # A cache-independent native snapshot makes the settled result recoverable
        # even when the external editable physics cache is not transferred.
        snapshot_mesh=bpy.data.meshes.new(f'{args.scene} / static settled snapshot')
        snapshot_mesh.from_pydata(vertices,[],payload['faces']);snapshot_mesh.update()
        layer=snapshot_mesh.uv_layers.new(name='Rest fabric direction')
        for face in snapshot_mesh.polygons:
            face.use_smooth=True
            for li in face.loop_indices:
                layer.data[li].uv=uv[snapshot_mesh.loops[li].vertex_index]
        snapshot=bpy.data.objects.new('SETTLED SNAPSHOT / unhide to inspect without cache',snapshot_mesh)
        bpy.context.collection.objects.link(snapshot)
        snapshot.hide_render=True;snapshot.hide_viewport=True
        snapshot['simulation_frame']=scene.frame_current
        snapshot['cache_independent']=True
        snapshot['source']='Actual evaluated Blender Cloth bake'
        payload['metadata']['snapshotObject']=snapshot.name
        output.write_text(json.dumps(payload),encoding='utf-8')
    finally:evaluated.to_mesh_clear()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print(json.dumps({'output':str(output),'blend':str(blend),'vertices':len(vertices),'frame':scene.frame_current,'baked':cache.is_baked}))


if __name__=='__main__':main()
