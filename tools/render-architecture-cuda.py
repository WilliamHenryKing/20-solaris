"""Original architectural material photographs, authored entirely in Blender Python.
Run through the project-local Blender binary:
  blender --background --factory-startup --python tools/render-architecture-cuda.py -- \
    --scene aurel --quality draft --output .workspace/architecture-refinement/aurel-draft.png
Use --validate to construct/save/inspect without rendering. CUDA GPU only; no CPU fallback.
All dimensions in metres. No borrowed geometry, textures, HDRI, or external libraries.
"""
import argparse
import json
import math
import random
import os
import sys
import time
from pathlib import Path
import bpy
from mathutils import Vector


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', choices=['aurel', 'strata', 'solaris'], required=True)
    parser.add_argument('--quality', choices=['draft', 'final'], default='draft')
    parser.add_argument('--output', required=True)
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--detail', action='store_true')
    parser.add_argument('--samples', type=int)
    return parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def cube(name, location, size, material, bevel=.01):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new('True eased architectural edges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
    return obj


def cylinder(name, location, radius, depth, material, vertices=96, bevel=.015):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    if bevel:
        modifier=obj.modifiers.new('Soft cast edge', 'BEVEL')
        modifier.width=bevel
        modifier.segments=3
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices)==4
    return obj


def material(name, dark, light, roughness=.65, scale=(5,5,5), metallic=0, grain=False):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    nodes.clear()
    links=mat.node_tree.links
    output=nodes.new('ShaderNodeOutputMaterial')
    principled=nodes.new('ShaderNodeBsdfPrincipled')
    principled.inputs['Metallic'].default_value=metallic
    principled.inputs['Roughness'].default_value=roughness
    links.new(principled.outputs['BSDF'],output.inputs['Surface'])
    coord=nodes.new('ShaderNodeTexCoord')
    mapping=nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value=scale
    links.new(coord.outputs['Object'],mapping.inputs['Vector'])
    broad=nodes.new('ShaderNodeTexNoise')
    broad.noise_dimensions='4D'
    info=nodes.new('ShaderNodeObjectInfo')
    shift=nodes.new('ShaderNodeMath')
    shift.operation='MULTIPLY'
    shift.inputs[1].default_value=73.19
    links.new(info.outputs['Random'],shift.inputs[0])
    links.new(shift.outputs[0],broad.inputs['W'])
    broad.inputs['Scale'].default_value=1.8 if grain else 2.4
    broad.inputs['Detail'].default_value=5
    broad.inputs['Roughness'].default_value=.72
    links.new(mapping.outputs['Vector'],broad.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.18
    ramp.color_ramp.elements[0].color=(*dark,1)
    ramp.color_ramp.elements[1].position=.85
    ramp.color_ramp.elements[1].color=(*light,1)
    links.new(broad.outputs['Fac'],ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'],principled.inputs['Base Color'])
    fine=nodes.new('ShaderNodeTexNoise')
    fine.inputs['Scale'].default_value=120 if grain else 190
    fine.inputs['Detail'].default_value=3
    links.new(mapping.outputs['Vector'],fine.inputs['Vector'])
    bumpFine=nodes.new('ShaderNodeBump')
    bumpFine.inputs['Strength'].default_value=.16 if metallic else .26
    bumpFine.inputs['Distance'].default_value=.0007 if metallic else .002
    links.new(fine.outputs['Fac'],bumpFine.inputs['Height'])
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.27 if grain else .18
    bump.inputs['Distance'].default_value=.0018 if grain else .001
    links.new(broad.outputs['Fac'],bump.inputs['Height'])
    links.new(bumpFine.outputs['Normal'],bump.inputs['Normal'])
    if 'travertine' in name.lower():
        pores=nodes.new('ShaderNodeTexVoronoi')
        pores.inputs['Scale'].default_value=135
        links.new(coord.outputs['Object'],pores.inputs['Vector'])
        holes=nodes.new('ShaderNodeValToRGB')
        holes.color_ramp.elements[0].position=.035
        holes.color_ramp.elements[0].color=(0,0,0,1)
        holes.color_ramp.elements[1].position=.16
        holes.color_ramp.elements[1].color=(1,1,1,1)
        links.new(pores.outputs['Distance'],holes.inputs['Fac'])
        porosity=nodes.new('ShaderNodeBump')
        porosity.inputs['Strength'].default_value=.45
        porosity.inputs['Distance'].default_value=.0015
        links.new(holes.outputs['Color'],porosity.inputs['Height'])
        links.new(bumpFine.outputs['Normal'],porosity.inputs['Normal'])
        links.new(porosity.outputs['Normal'],bump.inputs['Normal'])
    links.new(bump.outputs['Normal'],principled.inputs['Normal'])
    rough=nodes.new('ShaderNodeMapRange')
    rough.inputs['From Min'].default_value=0
    rough.inputs['From Max'].default_value=1
    rough.inputs['To Min'].default_value=max(.12,roughness-.08)
    rough.inputs['To Max'].default_value=min(1,roughness+.06)
    links.new(fine.outputs['Fac'],rough.inputs['Value'])
    links.new(rough.outputs['Result'],principled.inputs['Roughness'])
    return mat


def palette():
    return {
      'walnut':material('Oiled walnut / individual board growth',(.027,.014,.009),(.14,.068,.033),.44,(21,14,.18),grain=True),
      'oak':material('European oak / grain follows horizontal board length',(.24,.16,.08),(.39,.28,.15),.49,(.21,22,17),grain=True),
      'stone':material('Vein cut travertine / restrained mineral bands',(.44,.39,.29),(.63,.57,.43),.72,(.8,1.2,16)),
      'concrete':material('Warm cast concrete / quiet micro aggregate',(.52,.50,.44),(.58,.56,.50),.81,(5,5,5)),
      'clay':material('Hand trowelled clay / restrained earth pigment',(.32,.135,.082),(.385,.173,.113),.86,(3,3,3)),
      'brass':material('Satin aged brass / fine brushing',(.24,.135,.035),(.66,.45,.13),.29,(1,80,1),.88),
      'metal':material('Brushed aluminium / directional satin',(.34,.36,.38),(.72,.74,.77),.33,(1,95,1),.97),
      'ink':material('Deep mineral finish',(.014,.018,.022),(.04,.046,.047),.62),
      'plaster':material('Lime plaster / quiet handworked surface',(.62,.59,.51),(.68,.65,.56),.84,(3,3,3)),
      'floor':material('Honed limestone / subtle fine pores',(.42,.39,.33),(.49,.46,.39),.77,(3,3,3)),
    }


def tiles(mat, width=12, depth=12, pitch=1.2, z=-.075):
    # Real bevels and 3 mm joints; thin mesh slabs rather than a painted grid.
    cols=math.ceil(width/pitch)
    rows=math.ceil(depth/pitch)
    for i in range(cols):
        for j in range(rows):
            cube(f'Limestone floor {i:02}_{j:02}',((i-(cols-1)/2)*pitch,(j-(rows-1)/2)*pitch,z),(pitch-.003,pitch-.003,.15),mat,.004)


def slats(name, material, x0, y, z, count, pitch, width, depth, height):
    for i in range(count):
        cube(f'{name} / ridge {i:03}',(x0+i*pitch,y,z),(width,depth,height),material,.009)


def area(name, location, target, energy, color, size, size_y=None):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy
    data.color=color
    data.shape='RECTANGLE' if size_y else 'DISK'
    data.size=size
    if size_y:data.size_y=size_y
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location=location
    point_at(obj,target)
    return obj


def sun(location,target,energy=2.2,color=(1,.85,.65),angle=.035):
    data=bpy.data.lights.new('Sun / actual directional shadows','SUN')
    data.energy=energy
    data.color=color
    data.angle=angle
    obj=bpy.data.objects.new('Sun / actual directional shadows',data)
    bpy.context.collection.objects.link(obj)
    obj.location=location
    point_at(obj,target)


def camera(location,target,lens=48):
    data=bpy.data.cameras.new('Authored architectural composition')
    obj=bpy.data.objects.new('Authored architectural composition',data)
    bpy.context.collection.objects.link(obj)
    obj.location=location
    point_at(obj,target)
    data.lens=lens
    data.clip_end=200
    bpy.context.scene.camera=obj
    return obj


def annulus(name, inner, outer, height, material, z, segments=160):
    verts=[]
    for zz in [z-height/2,z+height/2]:
        for radius in [outer,inner]:
            for i in range(segments):
                a=i/segments*math.tau
                verts.append((math.cos(a)*radius,math.sin(a)*radius,zz))
    faces=[]
    for i in range(segments):
        j=(i+1)%segments
        faces.extend([(i,j,segments+j,segments+i),(2*segments+i,3*segments+i,3*segments+j,2*segments+j),(i,2*segments+i,2*segments+j,j),(segments+i,segments+j,3*segments+j,3*segments+i)])
    geo=bpy.data.meshes.new(name)
    geo.from_pydata(verts,[],faces)
    geo.update()
    obj=bpy.data.objects.new(name,geo)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bevel=obj.modifiers.new('Skylight arris easing','BEVEL')
    bevel.width=.024
    bevel.segments=3
    return obj


def curved_wall(name,radius,start,end,height,thickness,material):
    count=120
    verts=[]
    for z in [0,height]:
        for r in [radius,radius+thickness]:
            for i in range(count+1):
                a=start+(end-start)*i/count
                verts.append((math.cos(a)*r,math.sin(a)*r,z))
    n=count+1
    faces=[]
    for i in range(count):
        faces.extend([(i,i+1,n+i+1,n+i),(2*n+i,3*n+i,3*n+i+1,2*n+i+1),(i,2*n+i,2*n+i+1,i+1),(n+i,n+i+1,3*n+i+1,3*n+i)])
    faces.extend([(0,n,3*n,2*n),(count,2*n+count,3*n+count,n+count)])
    geo=bpy.data.meshes.new(name)
    geo.from_pydata(verts,[],faces)
    geo.update()
    obj=bpy.data.objects.new(name,geo)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    modifier=obj.modifiers.new('Concrete edge easing','BEVEL')
    modifier.width=.022
    modifier.segments=3
    return obj


def lathe_vessel(name,position,mat):
    # A continuous ceramic wall, actual open lip, inner cavity and foot ring.
    profile=[(.001,0),(.12,0),(.15,.025),(.185,.12),(.18,.27),(.13,.37),(.10,.41),(.11,.435),(.11,.448),(.088,.448),(.087,.43),(.085,.41),(.105,.365),(.15,.265),(.15,.13),(.11,.055),(.001,.055)]
    segments=128
    vertices=[(r*math.cos(i/segments*math.tau),r*math.sin(i/segments*math.tau),z) for r,z in profile for i in range(segments)]
    faces=[]
    for j in range(len(profile)-1):
        for i in range(segments):
            k=(i+1)%segments
            faces.append((j*segments+i,j*segments+k,(j+1)*segments+k,(j+1)*segments+i))
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    obj.location=position
    obj.data.materials.append(mat)
    for face in obj.data.polygons:face.use_smooth=True
    return obj


def olive_tree(position,materials):
    rng=random.Random(53)
    bark=material('Olive bark / fine furrowed trunk',(.07,.06,.035),(.15,.14,.08),.9,(15,15,.8),grain=True)
    leafmat=material('Olive leaves / dusty silver green',(.043,.065,.024),(.14,.17,.065),.61,(4,4,4))
    x,y,z=position
    cylinder('Olive planter exterior',(x,y,z+.28),.34,.56,materials['clay'],128,.012)
    cylinder('Dark earth in planter',(x,y,z+.565),.31,.015,materials['ink'],96,.001)
    def branch(a,b,r,name):
        delta=Vector(b)-Vector(a)
        obj=cylinder(name,(Vector(a)+Vector(b))/2,r,delta.length,bark,16,.003)
        obj.rotation_euler=delta.to_track_quat('Z','Y').to_euler()
        return obj
    trunk0=Vector((x,y,z+.55))
    trunk1=Vector((x-.08,y+.03,z+1.53))
    branch(trunk0,trunk1,.043,'Olive / sinuous trunk')
    for n in range(8):
        angle=n*2.399
        start=trunk1+Vector((0,0,rng.uniform(-.2,.15)))
        end=start+Vector((math.cos(angle)*rng.uniform(.32,.61),math.sin(angle)*rng.uniform(.32,.59),rng.uniform(.38,.76)))
        branch(start,end,.015,'Olive / tapered lateral branch')
        for j in range(22):
            t=rng.uniform(.24,1.04)
            centre=start.lerp(end,t)+Vector((rng.uniform(-.16,.16),rng.uniform(-.14,.14),rng.uniform(-.15,.16)))
            length=rng.uniform(.065,.105)
            verts=[(0,-length,0),(-.018,-length*.25,.006),(-.024,length*.25,.011),(0,length,.018),(.024,length*.25,.011),(.018,-length*.25,.006),(0,0,.016)]
            faces=[(6,i,(i+1)%6) for i in range(6)]
            mesh=bpy.data.meshes.new('Olive leaf / curved blade')
            mesh.from_pydata(verts,[],faces)
            mesh.update()
            obj=bpy.data.objects.new('Olive foliage / actual curved leaf',mesh)
            bpy.context.collection.objects.link(obj)
            obj.location=centre
            obj.rotation_euler=(rng.uniform(-.7,.7),rng.uniform(-.8,.8),angle+rng.uniform(-1,1))
            obj.data.materials.append(leafmat)
            for face in obj.data.polygons:face.use_smooth=True


def aurel(m, detail=False):
    tiles(m['floor'],10,10,pitch=1.1)
    cube('Walnut joinery backing',(0,2.5,2.42),(8.6,.3,4.84),m['walnut'],.015)
    # Every flute is physical geometry with eased corners, a 4 mm groove and uninterrupted tall grain.
    slats('Tall walnut cabinet flutes',m['walnut'],-4.22,2.28,2.42,120,.071,.067,.12,4.84)
    for x in [-1.05,1.08]:
        cube('Bronze vertical shadow gap',(x,2.2,1.6),(.009,.025,3.05),m['brass'],.003)
        cube('Bronze discreet door pull',(x+.035,2.11,1.52),(.018,.07,.42),m['brass'],.004)
    cube('Walnut toe kick',(0,2.4,.11),(6.35,.3,.2),m['ink'],.005)
    cube('Travertine island monolith',(-.18,-.04,.43),(2.9,1.05,.86),m['stone'],.025)
    cube('Travertine island honed top',(-.18,-.04,.915),(3.08,1.17,.13),m['stone'],.024)
    cube('Island fine brass reveal',(-.18,-.04,.833),(2.94,1.09,.012),m['brass'],.002)
    lathe_vessel('Hand thrown open lipped ceramic vessel',(0,-.05,.98),m['ink'])
    cylinder('Small stone object',(-.66,.03,1.015),.12,.08,m['stone'],96,.015)
    cube('Limewash side return / rear pier',(-4.38,3.4,2.42),(.23,3.8,4.84),m['plaster'],.012)
    cube('Limewash side return / front pier',(-4.38,-3.7,2.42),(.23,.8,4.84),m['plaster'],.012)
    cube('Limewash side window / deep head',(-4.38,-.8,4.43),(.23,5,.82),m['plaster'],.012)
    cube('Limewash side window / deep sill',(-4.38,-.8,.35),(.23,5,.7),m['plaster'],.012)
    cube('Limewash ceiling outside crop',(0,1,4.94),(11,12,.16),m['plaster'],.012)
    # Two external fins cut actual long daylight bands across cabinet and floor.
    for i in range(4):
        cube('External shade blade',(-4.05,-2.2+i*.47,2.3),(.13,.16,4.6),m['ink'],.008)
    sun((-7,-4,5),(0,1,1.3),2.35,(1,.79,.52),.026)
    area('Broad cool skylight',(-1,-3,5),(0,1,1),210,(.73,.82,1),5)
    area('Warm joinery grazing reflection',(4,1,3),(0,2,1.5),65,(1,.75,.46),2,3)
    camera((2.8,-3.5,1.55),(-.2,1.8,1.3),45) if not detail else camera((1.2,-.3,1.65),(.25,2.2,1.45),58)


def stone_arch(mat):
    outer=1.48
    inner=.88
    spring=1.82
    outline=[(-outer,0),(-outer,spring)]
    for i in range(97):
        a=math.pi-math.pi*i/96
        outline.append((math.cos(a)*outer,spring+math.sin(a)*outer))
    outline.extend([(outer,0),(inner,0),(inner,spring)])
    for i in range(97):
        a=math.pi*i/96
        outline.append((math.cos(a)*inner,spring+math.sin(a)*inner))
    outline.append((-inner,0))
    count=len(outline)
    verts=[(x,y,z) for y in [-.27,.27] for x,z in outline]
    faces=[tuple(range(count-1,-1,-1)),tuple(range(count,2*count))]
    faces.extend([(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)])
    geo=bpy.data.meshes.new('Solid continuous carved travertine arch')
    geo.from_pydata(verts,[],faces)
    geo.update()
    obj=bpy.data.objects.new('Solid carved travertine arch',geo)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.location=(-.8,.5,0)
    bevel=obj.modifiers.new('Honed stone arris','BEVEL')
    bevel.width=.025
    bevel.segments=4
    return obj


def strata(m, detail=False):
    tiles(m['floor'],12,12,pitch=1.5)
    cube('Infinite clay plaster gallery wall',(0,4.4,10),(50,.25,20),m['clay'],.015)
    stone_arch(m['stone'])
    cube('Fluted oak screen backing',(2.3,1.6,1.85),(1.3,.21,3.7),m['walnut'],.018)
    slats('Deep longitudinal timber ribs',m['walnut'],1.67,1.43,1.88,20,.065,.044,.17,3.64)
    cube('Brushed aluminium wing',(1.54,.27,1.1),(.065,.84,2.2),m['metal'],.014)
    cylinder('Grounded clay drum',(.95,-1.08,.58),.65,1.16,m['clay'],160,.04)
    cylinder('Travertine drum cap',(.95,-1.08,1.18),.69,.065,m['stone'],160,.012)
    cube('Fine bronze strip on clay plinth',(.95,-1.73,.7),(.71,.015,.014),m['brass'],.004)
    cube('Low brushed metal plane',(-1.65,-1.22,.17),(1.6,.8,.34),m['metal'],.022)
    sun((-6,-5,7),(0,0,1.5),2.0,(1,.89,.73),.048)
    area('Narrow raking strip for real grain',(4.2,1.15,3.5),(1.5,1.4,1.8),280,(1,.88,.71),.45,3.4)
    area('Large cool fill',(-3,-4,5),(0,0,1),95,(.78,.87,1),5)
    camera((5.7,-8.4,3.4),(.25,.7,1.5),55) if not detail else camera((3.8,-2.8,2.4),(1.85,1.1,1.9),62)


def solaris(m, detail=False):
    tiles(m['floor'],14,14,pitch=1.4)
    curved_wall('Curved concrete inhabited wall',4.15,.15,math.pi-.18,3.65,.24,m['concrete'])
    # An occupied full-scale room, open to the foreground with a true circular light aperture.
    roof=annulus('Floating concrete oculus roof',1.45,4.55,.24,m['concrete'],3.7)
    roof.location.y=.28
    for x in [-3.6,3.6]:
        cylinder('Slim bronze support',(x,-1.8,1.84),.055,3.68,m['brass'],32,.006)
    for i in range(15):
        cube('Oak bench slat / real longitudinal gap',(-1.32,-.3+i*.065,.49),(2.7,.054,.065),m['oak'],.009)
    for x in [-2.4,-.25]:
        cube('Oak bench solid support',(x,.13,.23),(.14,.76,.46),m['oak'],.012)
    cube('Bench support bronze footing',(-1.32,.13,.045),(2.8,.9,.035),m['brass'],.005)
    cylinder('Sculptural limestone low table',(1.6,.1,.31),.62,.62,m['stone'],160,.028)
    cylinder('Low table thin honed lip',(1.6,.1,.655),.78,.075,m['stone'],160,.02)
    cylinder('Small ceramic bowl',(1.6,.1,.73),.13,.085,m['ink'],96,.027)
    # Spatial rhythm and actual pergola shadows rather than a projected image.
    for i in range(12):
        beam=cube('External oak pergola blade',(-4.9+i*.34,-3.9,4.05),(.09,5.2,.15),m['oak'],.012)
        beam.rotation_euler.z=.08
    # Inset curved-wall brass joint gives the monolithic form a human-scale datum.
    for i in range(4):
        a=.32+i*.75
        obj=cube('Concrete vertical construction joint',(math.cos(a)*4.143,math.sin(a)*4.143,1.79),(.008,.015,3.48),m['ink'],.002)
        obj.rotation_euler.z=a
    olive_tree((2.6,2.1,0),m)
    sun((-2.5,-3,15),(0,1,0),2.8,(1,.93,.79),.022)
    area('Sky courtyard fill',(0,-3,6),(0,1,1),190,(.72,.85,1),6)
    area('Concrete edge reflection',(3,3,4),(0,1,1),80,(1,.89,.69),3)
    camera((2.9,-3.4,1.35),(-.1,1.3,1.45),28) if not detail else camera((.8,-4.9,1.5),(-1.25,.2,.55),55)


def configure(args):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='CUDA'
    prefs.refresh_devices()
    devices=[]
    for device in prefs.devices:
        device.use=device.type=='CUDA'
        if device.use:devices.append({'name':device.name,'type':device.type,'id':device.id})
    if not devices:raise RuntimeError('No CUDA Cycles device. Refusing CPU fallback.')
    scene.cycles.device='GPU'
    scene.cycles.samples=args.samples or (24 if args.quality=='draft' else 96)
    scene.cycles.use_denoising=True
    scene.cycles.denoiser='OPTIX'
    scene.cycles.adaptive_threshold=.025 if args.quality=='draft' else .012
    scene.cycles.max_bounces=8
    scene.cycles.diffuse_bounces=4
    scene.cycles.glossy_bounces=4
    scene.cycles.transmission_bounces=4
    scene.cycles.use_light_tree=True
    scene.render.resolution_x=800 if args.quality=='draft' else 2000
    scene.render.resolution_y=500 if args.quality=='draft' else 1250
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.color_depth='8'
    scene.render.film_transparent=False
    scene.render.threads_mode='FIXED'
    scene.render.threads=6
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=0
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.45,.55,.75,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.16
    return scene,devices


def main():
    args=arguments()
    output=Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    started=time.time()
    scene,devices=configure(args)
    globals()[args.scene](palette(),args.detail)
    scene.render.filepath=str(output)
    deps=bpy.context.evaluated_depsgraph_get()
    vertices=0
    triangles=0
    for obj in scene.objects:
        if obj.type!='MESH':continue
        evaluated=obj.evaluated_get(deps)
        mesh=evaluated.to_mesh()
        mesh.calc_loop_triangles()
        vertices+=len(mesh.vertices)
        triangles+=len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
    metadata={'scene':args.scene,'quality':args.quality,'detail':args.detail,'original':True,'provenance':'Original Blender Python geometry and procedural node materials; no external assets','blender':bpy.app.version_string,'binary':bpy.app.binary_path,'engine':'CYCLES','compute':'CUDA','devices':devices,'cpuEnabled':False,'denoiser':'OPTIX','resolution':[scene.render.resolution_x,scene.render.resolution_y],'samples':scene.cycles.samples,'objects':len(scene.objects),'materials':len(bpy.data.materials),'evaluatedVertices':vertices,'evaluatedTriangles':triangles,'rendered':False,'output':str(output),'blend':str(output.with_suffix('.blend'))}
    bpy.ops.wm.save_as_mainfile(filepath=metadata['blend'])
    if not args.validate:
        bpy.ops.render.render(write_still=True)
        metadata['rendered']=True
        metadata['bytes']=output.stat().st_size
    metadata['elapsedSeconds']=round(time.time()-started,3)
    output.with_suffix('.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('ARCHITECTURE_RESULT '+json.dumps(metadata))


if __name__=='__main__':main()
