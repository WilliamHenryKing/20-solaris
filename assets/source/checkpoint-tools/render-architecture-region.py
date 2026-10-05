"""Render one overscanned pixel region from a packed, full-camera CUDA world.

Region coordinates use the top-left origin of the final PNG. The camera and
full-frame resolution never change. Only the saved image border is cropped.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
import bpy


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blend',required=True)
    p.add_argument('--metadata',help='Verified immutable scene-construction receipt')
    p.add_argument('--region',type=int,nargs=4,required=True)
    p.add_argument('--scene',required=True)
    p.add_argument('--view',required=True)
    p.add_argument('--quality',required=True)
    p.add_argument('--samples',type=int)
    p.add_argument('--output',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    source=Path(args.blend).resolve();output=Path(args.output).resolve()
    metadata=Path(args.metadata).resolve() if args.metadata else source.with_suffix('.json')
    meta=json.loads(metadata.read_text(encoding='utf-8-sig'))
    if any(meta[key]!=getattr(args,key) for key in ('scene','view','quality')):
        raise ValueError('Packed scene identity does not match requested region')
    started=time.time()
    source_hash=digest(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene=bpy.context.scene
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='CUDA';prefs.get_devices()
    selected=[]
    for device in prefs.devices:
        device.use=device.type=='CUDA'
        if device.use:selected.append({'name':device.name,'type':device.type,'id':device.id})
    if not selected:raise RuntimeError('No CUDA GPU available; CPU fallback is prohibited')
    scene.cycles.device='GPU'
    scene.render.use_persistent_data=False
    scene.cycles.tile_size=512
    if args.samples:scene.cycles.samples=args.samples
    width,height=scene.render.resolution_x,scene.render.resolution_y
    x0,y0,x1,y1=args.region
    if not(0<=x0<x1<=width and 0<=y0<y1<=height):raise ValueError('Invalid pixel bounds')
    scene.render.use_border=True
    scene.render.use_crop_to_border=True
    # A tiny subpixel offset avoids float32 rounding an intended integer border
    # down by one pixel. It does not move the camera or the sampled pixel grid.
    def edge(pixel,extent):return min(1.0,(pixel+.01)/extent)
    scene.render.border_min_x=edge(x0,width)
    scene.render.border_max_x=edge(x1,width)
    scene.render.border_min_y=edge(height-y1,height)
    scene.render.border_max_y=edge(height-y0,height)
    scene.render.filepath=str(output)
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_depth='16'
    output.parent.mkdir(parents=True,exist_ok=True)
    print(f'REGION {args.region} within {width}x{height}; CUDA; samples {scene.cycles.samples}',flush=True)
    bpy.ops.render.render(write_still=True)
    with output.open('rb') as stream:header=stream.read(24)
    dimensions=list(struct.unpack('>II',header[16:24]))
    if dimensions!=[x1-x0,y1-y0]:
        raise RuntimeError(f'Unexpected cropped dimensions {dimensions}; expected {[x1-x0,y1-y0]}')
    record={'scene':args.scene,'view':args.view,'quality':args.quality,'rendered':True,
            'sourceBlend':str(source),'sourceBlendSha256':source_hash,'region':args.region,
            'fullResolution':[width,height],'resolution':dimensions,'compute':'CUDA','devices':selected,
            'cpuEnabled':False,'denoiser':scene.cycles.denoiser,'samples':scene.cycles.samples,
            'adaptiveThreshold':scene.cycles.adaptive_threshold,'minimumSamples':scene.cycles.adaptive_min_samples,
            'bounces':scene.cycles.max_bounces,'blender':bpy.app.version_string,'tileSize':scene.cycles.tile_size,
            'bytes':output.stat().st_size,'sha256':digest(output),'elapsedSeconds':round(time.time()-started,3)}
    output.with_suffix('.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('REGION_RESULT '+json.dumps(record),flush=True)


if __name__=='__main__':main()
