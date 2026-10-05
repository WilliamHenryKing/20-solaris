"""CUDA architectural worlds. Original scenes plus licensed photographic PBR.
Use --scene solaris --view wide|detail --quality draft|final --output.
"""
import argparse
import importlib
import json
import hashlib
import sys
import time
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(Path(__file__).resolve().parent/'worlds'))
import world_common as common

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--scene',choices=['solaris'],required=True)
    p.add_argument('--view',choices=['wide','detail'],default='wide')
    p.add_argument('--quality',choices=['draft','final'],default='draft')
    p.add_argument('--output',required=True)
    p.add_argument('--samples',type=int)
    p.add_argument('--validate',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    output=Path(args.output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    started=time.time()
    scene,devices=common.base.configure(args)
    print(f'WORLD_PHASE configured CUDA for {args.scene} / {args.view}',flush=True)
    scene.render.resolution_x=1000 if args.quality=='draft' else 3200
    scene.render.resolution_y=625 if args.quality=='draft' else 2000
    scene.render.image_settings.color_depth='16'
    scene.cycles.samples=args.samples or (64 if args.quality=='draft' else (768 if args.view=='wide' else 1024))
    scene.cycles.adaptive_threshold=.03 if args.quality=='draft' else .005
    scene.cycles.adaptive_min_samples=16 if args.quality=='draft' else 96
    scene.cycles.max_bounces=14
    scene.cycles.diffuse_bounces=6
    scene.cycles.glossy_bounces=6
    scene.cycles.transmission_bounces=10
    scene.cycles.transparent_max_bounces=12
    scene.cycles.sample_clamp_indirect=8
    scene.render.use_persistent_data=False
    # Cache small image tiles to disk instead of retaining a 2048px tile's
    # buffers. Pixel resolution, sampling and material fidelity are unchanged.
    scene.cycles.tile_size=512
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=.25 if args.scene=='aurel' else .55
    textures=ROOT/'assets/source/textures'
    common.environment(textures,rotation=.4,strength=.5)
    module=importlib.import_module(args.scene)
    module.build(common.palette(textures),args.view)
    # The shared construction palette contains alternatives not used by every
    # residence. Remove only unreferenced datablocks, preserving all scene assets.
    bpy.data.orphans_purge(do_recursive=True)
    print(f'WORLD_PHASE geometry built: {len(scene.objects)} objects',flush=True)
    for obj in scene.objects:
        if obj.type=='MESH' and obj.get('uv_kind')=='cylindrical':
            common.uv_cylindrical(obj)
        if obj.type=='MESH' and not obj.data.uv_layers:
            common.uv_project(obj)
    scene.render.filepath=str(output)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend')),compress=True)
    print('WORLD_PHASE packed editable scene saved',flush=True)
    triangles=0
    deps=bpy.context.evaluated_depsgraph_get()
    for obj in scene.objects:
        if obj.type not in ['MESH','CURVE']:continue
        eval_obj=obj.evaluated_get(deps)
        mesh=eval_obj.to_mesh()
        if mesh:
            mesh.calc_loop_triangles()
            triangles+=len(mesh.loop_triangles)
        eval_obj.to_mesh_clear()
    metadata={'scene':args.scene,'view':args.view,'quality':args.quality,'compute':'CUDA','devices':devices,'cpuEnabled':False,'denoiser':'OPTIX','blender':bpy.app.version_string,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'samples':scene.cycles.samples,'adaptiveThreshold':scene.cycles.adaptive_threshold,'minimumSamples':scene.cycles.adaptive_min_samples,'bounces':scene.cycles.max_bounces,'objects':len(scene.objects),'evaluatedTriangles':triangles,'geometry':'Original Python authored architectural world','materials':'Original procedural and Poly Haven CC0 photo PBR; see assets/source/texture-manifest.json','texturesPacked':True,'rendered':False}
    cloth_source=Path(common.__file__).parent/'cloth'/f'{args.scene}.json'
    metadata['cloth']={'sha256':hashlib.sha256(cloth_source.read_bytes()).hexdigest(),'bake':json.loads(cloth_source.read_text())['metadata']}
    metadata['tileSize']=scene.cycles.tile_size
    output.with_suffix('.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    if not args.validate:
        print(f'WORLD_PHASE rendering {scene.render.resolution_x}x{scene.render.resolution_y}; cap {scene.cycles.samples}; threshold {scene.cycles.adaptive_threshold}',flush=True)
        bpy.ops.render.render(write_still=True)
        metadata['rendered']=True
        metadata['bytes']=output.stat().st_size
    metadata['elapsedSeconds']=round(time.time()-started,3)
    output.with_suffix('.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print('WORLD_RESULT '+json.dumps(metadata),flush=True)

if __name__=='__main__':main()
