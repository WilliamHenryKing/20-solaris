"""Resume guarded architectural stills from eight independently verified regions.

Run with the ordinary Python environment that contains OpenCV and NumPy, not
inside Blender. This process starts only one guarded Blender child at a time.
Default: all three worlds, wide then detail, at 3200x2000 / final settings.
Use --scene aurel --view wide to select one image; --quality draft is a separate
1000x625 checkpoint namespace for a bounded pipeline proof.

A successful scene-construction receipt is never evidence of a rendered PNG.
Raw construction/region receipts remain in the checkpoint directory. The final
machine receipt is published only after all regions and the saved full PNG pass.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import time
import uuid
import zlib


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / '.workspace/architecture-worlds'
GUARD = ROOT / 'tools/render-architecture-guard.py'
SCENES = ('aurel', 'strata', 'solaris')
VIEWS = ('wide', 'detail')
COLS, ROWS, OVERSCAN = 4, 2, 64
METHOD = 'checkpointed border regions with 64px overscan'
SCHEMA = 1
COLOR_CHUNKS = {b'iCCP', b'sRGB', b'gAMA', b'cHRM'}


@contextmanager
def queue_lock():
    """OS-owned lock, released on process exit; the harmless file may persist."""
    directory = OUTPUT / 'checkpoints'
    directory.mkdir(parents=True, exist_ok=True)
    stream = (directory / 'queue.lock').open('a+b')
    locked = False
    try:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as error:
            raise RuntimeError('The checkpointed-world queue is already locked by another process; no image/status files were changed.') from error
        yield
    finally:
        if locked:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def read_json(path):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError(f'Expected a JSON object: {path}')
    return value


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    try:
        with temp.open('w', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def settings_for(view, quality, samples=None):
    draft = quality == 'draft'
    return {
        'resolution': [1000, 625] if draft else [3200, 2000],
        'samples': samples or (64 if draft else (768 if view == 'wide' else 1024)),
        'adaptiveThreshold': .03 if draft else .005,
        'minimumSamples': 16 if draft else 96,
        'bounces': 14,
        'compute': 'CUDA',
        'cpuEnabled': False,
        'denoiser': 'OPTIX',
    }


def fingerprint(scene, view, quality, settings):
    # Render settings are covered both by the Python source hashes and this
    # explicit contract. Cloth geometry and the texture attribution/hash manifest
    # are inputs; no bpy import or scene construction occurs in this process.
    paths = [
        Path(__file__).resolve(), GUARD,
        ROOT / 'tools/render-architecture-region.py',
        ROOT / 'tools/render-architecture-world.py',
        ROOT / 'tools/render-architecture-cuda.py',
        ROOT / 'tools/worlds/world_common.py',
        ROOT / f'tools/worlds/{scene}.py',
        ROOT / f'tools/worlds/cloth/{scene}.json',
        OUTPUT / 'textures/manifest.json',
    ]
    cloth_meta = ROOT / f'tools/worlds/cloth/{scene}.metadata.json'
    if cloth_meta.exists():
        paths.append(cloth_meta)
    sources = {relative(path): digest(path) for path in paths}
    texture_root = (OUTPUT / 'textures').resolve()
    manifest = read_json(texture_root / 'manifest.json')
    for asset in manifest['assets']:
        for entry in asset['files']:
            path = (texture_root / entry['file']).resolve()
            path.relative_to(texture_root)
            actual_sha = digest(path)
            if actual_sha != entry['sha256'] or path.stat().st_size != entry['bytes']:
                raise ValueError(f'Texture/HDRI bytes do not match their source manifest: {path}')
            sources[relative(path)] = actual_sha
            paths.append(path)
    runtime = ROOT / '.workspace/blender-runtime/Blender Foundation/Blender 5.2/blender.exe'
    runtime_stat = runtime.stat()
    contract = {
        'schema': SCHEMA, 'scene': scene, 'view': view, 'quality': quality,
        'settings': settings, 'grid': [COLS, ROWS], 'overscan': OVERSCAN,
        'sources': sources,
        'blenderRuntime': {'path': relative(runtime), 'bytes': runtime_stat.st_size,
                           'mtimeNs': runtime_stat.st_mtime_ns},
    }
    encoded = json.dumps(contract, sort_keys=True, separators=(',', ':')).encode()
    # The new orchestrator itself cannot make an earlier full image visually
    # stale; every actual scene/renderer/guard input and the runtime can.
    newest = max(path.stat().st_mtime_ns for path in paths if path != Path(__file__).resolve())
    return hashlib.sha256(encoded).hexdigest(), contract, max(newest, runtime_stat.st_mtime_ns)


def regions(width, height):
    for row in range(ROWS):
        for col in range(COLS):
            core = [col * width // COLS, row * height // ROWS,
                    (col + 1) * width // COLS, (row + 1) * height // ROWS]
            bounds = [max(0, core[0] - OVERSCAN), max(0, core[1] - OVERSCAN),
                      min(width, core[2] + OVERSCAN), min(height, core[3] + OVERSCAN)]
            yield {'id': f'r{row + 1}-c{col + 1}', 'core': core, 'region': bounds}


def identity(meta, scene, view, quality):
    for key, expected in [('scene', scene), ('view', view), ('quality', quality)]:
        if meta.get(key) != expected:
            raise ValueError(f'Receipt {key} mismatch: {meta.get(key)!r} != {expected!r}')


def validate_settings(meta, settings, tile=False):
    for key, expected in settings.items():
        if tile and key == 'resolution':
            key = 'fullResolution'
        actual = meta.get(key)
        # Blender stores these values as float32; keep its original receipt
        # precision while accepting representation noise at the contract check.
        matches = (type(actual) in (int, float)
                   and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-9)) \
            if type(expected) is float else actual == expected
        if not matches:
            raise ValueError(f'Render setting {key} mismatch: {actual!r} != {expected!r}')


def validate_machine(path, scene, view, quality):
    machine = read_json(path)
    identity(machine, scene, view, quality)
    if type(machine.get('exitCode')) is not int or machine['exitCode'] != 0:
        raise ValueError(f'Unsuccessful renderer exit: {path}')
    if machine.get('guardStopped') is not False or machine.get('monitorError'):
        raise ValueError(f'Guard did not finish cleanly: {path}')
    guards, samples = machine.get('guards'), machine.get('samples')
    if not isinstance(guards, dict) or not isinstance(samples, list) or not samples:
        raise ValueError(f'Missing raw machine samples/thresholds: {path}')
    checks = [('gpuC', 'maxGpuC', lambda value, limit: value < limit),
              ('freeVramMiB', 'minFreeVramMiB', lambda value, limit: value >= limit),
              ('freeRamMiB', 'minFreeRamMiB', lambda value, limit: value >= limit)]
    for sample in samples:
        for field, threshold, compare in checks:
            value, limit = sample.get(field), guards.get(threshold)
            if (not isinstance(value, (int, float)) or not math.isfinite(value)
                    or not isinstance(limit, (int, float)) or not math.isfinite(limit)
                    or not compare(value, limit)):
                raise ValueError(f'Invalid/breached {field} evidence: {path}')
    return machine


def image_data(path, dimensions):
    import cv2
    import numpy as np
    # OpenCV's unchanged BGR(A) order is retained on both decode and encode.
    pixels = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if (pixels is None or pixels.dtype != np.uint16 or pixels.ndim != 3
            or pixels.shape[2] not in (3, 4)
            or list(pixels.shape[1::-1]) != dimensions):
        raise ValueError(f'Expected {dimensions} uint16 RGB(A) PNG: {path}')
    return pixels


def color_chunks(path):
    """Read raw, CRC-checked PNG colour chunks without interpreting their data."""
    chunks, seen = [], set()
    with Path(path).open('rb') as stream:
        if stream.read(8) != b'\x89PNG\r\n\x1a\n':
            raise ValueError(f'Not a PNG: {path}')
        while True:
            header = stream.read(8)
            if len(header) != 8:
                raise ValueError(f'Truncated PNG chunk header: {path}')
            length, kind = struct.unpack('>I4s', header)
            if stream.tell() + length + 4 > Path(path).stat().st_size:
                raise ValueError(f'Truncated PNG chunk: {path}')
            if kind in COLOR_CHUNKS:
                if kind in seen:
                    raise ValueError(f'Duplicate colour chunk {kind!r}: {path}')
                data, crc = stream.read(length), stream.read(4)
                if zlib.crc32(kind + data) != struct.unpack('>I', crc)[0]:
                    raise ValueError(f'Invalid colour chunk CRC: {path}')
                chunks.append(header + data + crc)
                seen.add(kind)
            else:
                stream.seek(length + 4, 1)
            if kind == b'IEND':
                return chunks


def preserve_color_chunks(path, chunks):
    """Insert original colour metadata after IHDR; never transform pixel values."""
    replacement = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.colour.png')
    try:
        with path.open('rb') as source, replacement.open('wb') as dest:
            signature = source.read(8)
            if signature != b'\x89PNG\r\n\x1a\n':
                raise ValueError('OpenCV output lacks the PNG signature.')
            dest.write(signature)
            first = True
            while True:
                header = source.read(8)
                if len(header) != 8:
                    raise ValueError('Truncated assembled PNG.')
                length, kind = struct.unpack('>I4s', header)
                if first and (kind != b'IHDR' or length != 13):
                    raise ValueError('Assembled PNG has no leading IHDR.')
                if kind in COLOR_CHUNKS:
                    source.seek(length + 4, 1)
                else:
                    dest.write(header)
                    remaining = length + 4
                    while remaining:
                        block = source.read(min(remaining, 1024 * 1024))
                        if not block:
                            raise ValueError('Truncated assembled PNG data.')
                        dest.write(block)
                        remaining -= len(block)
                if first:
                    for chunk in chunks:
                        dest.write(chunk)
                    first = False
                if kind == b'IEND':
                    break
            dest.flush()
            os.fsync(dest.fileno())
        os.replace(replacement, path)
        if color_chunks(path) != chunks:
            raise ValueError('PNG colour metadata did not survive assembly.')
    finally:
        replacement.unlink(missing_ok=True)


def file_receipt(path):
    path = Path(path)
    return {'path': relative(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def verify_file(record):
    path = (ROOT / record['path']).resolve()
    path.relative_to(ROOT)
    if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
        raise ValueError(f'File no longer matches its receipt: {path}')
    return path


def verify_region(path, spec, blend_hash, scene, view, quality, settings, previous=None):
    meta = read_json(path.with_suffix('.json'))
    identity(meta, scene, view, quality)
    validate_settings(meta, settings, tile=True)
    if (meta.get('rendered') is not True or meta.get('region') != spec['region']
            or meta.get('sourceBlendSha256') != blend_hash):
        raise ValueError(f'Region is incomplete or belongs to a different scene: {path}')
    x0, y0, x1, y1 = spec['region']
    dimensions = [x1 - x0, y1 - y0]
    if meta.get('resolution') != dimensions or meta.get('bytes') != path.stat().st_size:
        raise ValueError(f'Region dimensions/bytes receipt mismatch: {path}')
    png_hash = digest(path)
    if meta.get('sha256') != png_hash:
        raise ValueError(f'Region PNG hash differs from renderer receipt: {path}')
    if not (path.stat().st_mtime_ns <= path.with_suffix('.json').stat().st_mtime_ns
            <= path.with_suffix('.machine.json').stat().st_mtime_ns):
        raise ValueError(f'Region receipts predate the rendered PNG: {path}')
    pixels = image_data(path, dimensions)
    channels = pixels.shape[2]
    del pixels
    validate_machine(path.with_suffix('.machine.json'), scene, view, quality)
    record = {**spec, 'dimensions': dimensions, 'channels': channels, 'dtype': 'uint16',
              'sourceBlendSha256': blend_hash, 'png': file_receipt(path),
              'metadata': file_receipt(path.with_suffix('.json')),
              'machine': file_receipt(path.with_suffix('.machine.json'))}
    if previous is not None and record != previous:
        raise ValueError(f'Completed region changed since checkpoint: {path}')
    return record


def run_guard(arguments, expected_paths):
    start_ns = time.time_ns()
    command = [sys.executable, str(GUARD), *arguments]
    # No shell; inherit progress output. The guard owns monitoring and cleanup
    # of its child. An ordinary interruption reaches both console processes.
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f'Guard exited {result.returncode}; completed regions retained.')
    for path in expected_paths:
        if not path.is_file() or path.stat().st_mtime_ns < start_ns:
            raise RuntimeError(f'Guard did not produce a fresh artifact: {path}')


def assemble(output, receipts, dimensions):
    import cv2
    import numpy as np
    channels = receipts[0]['channels']
    if any(item['channels'] != channels for item in receipts):
        raise ValueError('Region channel counts differ; refusing implicit conversion.')
    first_chunks = color_chunks(verify_file(receipts[0]['png']))
    if any(color_chunks(verify_file(item['png'])) != first_chunks for item in receipts[1:]):
        raise ValueError('Regions have different PNG colour metadata; refusing to combine.')
    width, height = dimensions
    full = np.empty((height, width, channels), dtype=np.uint16)
    covered = np.zeros((height, width), dtype=np.uint8)
    for item in receipts:
        tile = image_data(verify_file(item['png']), item['dimensions'])
        x0, y0, x1, y1 = item['core']
        bx0, by0, _, _ = item['region']
        if covered[y0:y1, x0:x1].any():
            raise ValueError('Overlapping region cores.')
        full[y0:y1, x0:x1] = tile[y0 - by0:y1 - by0, x0 - bx0:x1 - bx0]
        covered[y0:y1, x0:x1] = 1
        del tile
    if not covered.all():
        raise ValueError('Region cores leave unfilled pixels.')
    del covered
    temp = output.with_name(f'.{output.stem}.{uuid.uuid4().hex}.pending.png')
    try:
        if not cv2.imwrite(str(temp), full, [cv2.IMWRITE_PNG_COMPRESSION, 3]):
            raise RuntimeError('OpenCV failed to save the assembled PNG.')
        preserve_color_chunks(temp, first_chunks)
        saved = image_data(temp, dimensions)
        if not np.array_equal(saved, full):
            raise ValueError('Saved PNG did not preserve the assembled uint16 pixels.')
        del full, saved
        with temp.open('rb+') as stream:
            os.fsync(stream.fileno())
        os.replace(temp, output)
        # Validate the actual published file before any complete receipt exists.
        saved = image_data(output, dimensions)
        del saved
        return {**file_receipt(output), 'colorChunks': [
            {'type': chunk[4:8].decode('ascii'), 'sha256': hashlib.sha256(chunk).hexdigest()}
            for chunk in first_chunks]}
    finally:
        temp.unlink(missing_ok=True)


def aggregate_machine(records, scene, view, quality):
    machines = []
    for name, receipt in records:
        path = verify_file(receipt)
        machines.append((name, validate_machine(path, scene, view, quality)))
    guards = machines[0][1]['guards']
    if any(machine['guards'] != guards for _, machine in machines):
        raise ValueError('Machine guard thresholds changed between phases.')
    samples = [{**sample, 'phase': name} for name, machine in machines
               for sample in machine['samples']]
    # Retain each phase's measured clock rather than inventing continuous
    # monitoring during the hours/days between separate resumptions.
    ranges = {}
    for sample in samples:
        for key, value in sample.items():
            if key != 'elapsedSeconds' and type(value) in (int, float) and math.isfinite(value):
                previous = ranges.setdefault(key, {'min': value, 'max': value})
                previous['min'] = min(previous['min'], value)
                previous['max'] = max(previous['max'], value)
    return {
        'scene': scene, 'view': view, 'quality': quality, 'operation': 'checkpointed-image',
        'renderMethod': METHOD, 'guards': guards,
        'exitCode': max(machine['exitCode'] for _, machine in machines),
        'guardStopped': any(machine['guardStopped'] for _, machine in machines),
        'elapsedSeconds': round(sum(machine['elapsedSeconds'] for _, machine in machines), 3),
        'timeBasis': 'sum of guarded phases; raw sample times are local to named phase',
        'maxGpuC': max(sample['gpuC'] for sample in samples),
        'minFreeVramMiB': min(sample['freeVramMiB'] for sample in samples),
        'minFreeRamMiB': min(sample['freeRamMiB'] for sample in samples),
        'sampleRanges': ranges, 'samples': samples,
        'coolingPeriods': [{**period, 'phase': name} for name, machine in machines
                           for period in machine.get('coolingPeriods', [])],
        'phaseReceipts': [{'phase': name, **receipt} for name, receipt in records],
        'validatedAt': now(),
    }


def reusable_full(output, scene, view, quality, settings, newest_source):
    """A prior ordinary full render may be adopted only with fresh evidence."""
    paths = [output, output.with_suffix('.blend'), output.with_suffix('.json'),
             output.with_suffix('.machine.json')]
    if not all(path.is_file() and path.stat().st_mtime_ns >= newest_source for path in paths):
        return None
    meta = read_json(output.with_suffix('.json'))
    if meta.get('renderMethod') == METHOD:
        return None  # Checkpointed images must retain and validate their tile chain.
    identity(meta, scene, view, quality)
    validate_settings(meta, settings)
    if meta.get('rendered') is not True or meta.get('bytes') != output.stat().st_size:
        return None
    validate_machine(output.with_suffix('.machine.json'), scene, view, quality)
    pixels = image_data(output, settings['resolution'])
    del pixels
    if 'sha256' in meta and meta['sha256'] != digest(output):
        raise ValueError('Existing full PNG hash differs from its render receipt.')
    return {'png': file_receipt(output), 'blend': file_receipt(output.with_suffix('.blend')),
            'metadata': file_receipt(output.with_suffix('.json')),
            'machine': file_receipt(output.with_suffix('.machine.json'))}


def render_job(scene, view, args):
    quality = args.quality
    settings = settings_for(view, quality, args.samples)
    source_hash, contract, newest_source = fingerprint(scene, view, quality, settings)
    checkpoint = OUTPUT / 'checkpoints' / f'{scene}-{view}'
    if quality != 'final':
        checkpoint = checkpoint / quality
    checkpoint.mkdir(parents=True, exist_ok=True)
    manifest_path = checkpoint / 'manifest.json'
    output = OUTPUT / f'{scene}-{view}-{quality}.png'
    blend = output.with_suffix('.blend')
    old = read_json(manifest_path) if manifest_path.exists() else {}
    same = old.get('sourceFingerprint') == source_hash
    manifest = old if same else {
        'schema': SCHEMA, 'scene': scene, 'view': view, 'quality': quality,
        'sourceFingerprint': source_hash, 'sourceContract': contract,
        'createdAt': now(), 'complete': False, 'tiles': {},
    }

    def persist(status):
        manifest.update(status=status, updatedAt=now())
        atomic_json(manifest_path, manifest)

    def unchanged():
        current, _, _ = fingerprint(scene, view, quality, settings)
        if current != source_hash:
            raise RuntimeError('Source changed during this job. Stop and resume against the new fingerprint.')

    try:
        try:
            existing = reusable_full(output, scene, view, quality, settings, newest_source)
        except (OSError, ValueError, KeyError):
            existing = None
        if existing:
            manifest.update(complete=True, existingFullRender=existing)
            persist('complete')
            print(f'CHECKPOINT {scene}/{view}: reused verified existing full render.', flush=True)
            return

        manifest['complete'] = False
        persist('preparing')
        build = manifest.get('construction')
        valid_build = False
        if build:
            try:
                if verify_file(build['blend']) != blend:
                    raise ValueError('Construction points to another scene file.')
                meta = read_json(verify_file(build['metadata']))
                identity(meta, scene, view, quality)
                validate_settings(meta, settings)
                if meta.get('rendered') is not False:
                    raise ValueError('Construction receipt must be construction-only.')
                validate_machine(verify_file(build['machine']), scene, view, quality)
                valid_build = True
            except (OSError, ValueError, KeyError):
                valid_build = False
        if not valid_build:
            print(f'CHECKPOINT {scene}/{view}: construct and pack scene (no render).', flush=True)
            # Keep old evidence intact in fingerprint/attempt-specific directories.
            attempt = checkpoint / 'construction-history' / f'{source_hash[:16]}-{uuid.uuid4().hex[:8]}'
            attempt.mkdir(parents=True)
            command = ['--world', '--validate', '--scene', scene, '--view', view,
                       '--quality', quality, '--output', str(output)]
            if args.samples:
                command += ['--samples', str(args.samples)]
            try:
                run_guard(command, [blend, output.with_suffix('.json'), output.with_suffix('.machine.json')])
            finally:
                for suffix, name in [('.json', 'construction.json'), ('.machine.json', 'construction.machine.json'), ('.log', 'construction.log')]:
                    current = output.with_suffix(suffix)
                    if current.exists():
                        shutil.copy2(current, attempt / name)
            unchanged()
            meta = read_json(attempt / 'construction.json')
            identity(meta, scene, view, quality)
            validate_settings(meta, settings)
            if meta.get('rendered') is not False:
                raise ValueError('Build unexpectedly claimed a completed render.')
            validate_machine(attempt / 'construction.machine.json', scene, view, quality)
            build = {'blend': file_receipt(blend), 'metadata': file_receipt(attempt / 'construction.json'),
                     'machine': file_receipt(attempt / 'construction.machine.json')}
            manifest.update(construction=build, tiles={})
            # Convenient latest construction receipts; immutable history above is authoritative.
            shutil.copy2(attempt / 'construction.json', checkpoint / 'construction.json')
            shutil.copy2(attempt / 'construction.machine.json', checkpoint / 'construction.machine.json')
            persist('scene-ready')
        else:
            print(f'CHECKPOINT {scene}/{view}: packed scene SHA and source fingerprint verified; no rebuild.', flush=True)

        blend_hash = build['blend']['sha256']
        tile_dir = checkpoint / 'regions' / f'{source_hash[:16]}-{blend_hash[:16]}'
        tile_dir.mkdir(parents=True, exist_ok=True)
        receipts = []
        specs = list(regions(*settings['resolution']))
        for number, spec in enumerate(specs, 1):
            unchanged()
            path = tile_dir / f"{spec['id']}.png"
            previous = manifest['tiles'].get(spec['id'])
            try:
                receipt = verify_region(path, spec, blend_hash, scene, view, quality, settings, previous)
                action = 'verified/reused'
            except (OSError, ValueError, KeyError):
                persist('rendering')
                print(f"CHECKPOINT {scene}/{view}: region {number}/{len(specs)} {spec['id']} render {spec['region']}", flush=True)
                command = ['--blend', str(blend), '--region', *map(str, spec['region']),
                           '--metadata', str(verify_file(build['metadata'])),
                           '--scene', scene, '--view', view, '--quality', quality, '--output', str(path)]
                if args.samples:
                    command += ['--samples', str(args.samples)]
                run_guard(command, [path, path.with_suffix('.json'), path.with_suffix('.machine.json')])
                unchanged()
                receipt = verify_region(path, spec, blend_hash, scene, view, quality, settings)
                action = 'saved/verified'
            manifest['tiles'][spec['id']] = receipt
            receipts.append(receipt)
            persist('regions-in-progress')
            print(f"CHECKPOINT {scene}/{view}: region {number}/{len(specs)} {spec['id']} {action}.", flush=True)

        unchanged()
        verify_file(build['blend'])
        # Validate every receipt again at publication, including any just rendered.
        receipts = [verify_region(tile_dir / f"{spec['id']}.png", spec, blend_hash,
                                  scene, view, quality, settings, manifest['tiles'][spec['id']])
                    for spec in specs]
        records = [('construction', build['machine'])] + [(item['id'], item['machine']) for item in receipts]
        machine = aggregate_machine(records, scene, view, quality)
        completed = manifest.get('full')
        if completed:
            try:
                verify_file(completed['png'])
                verify_file(completed['metadata'])
                verify_file(completed['machine'])
                final_meta = read_json(output.with_suffix('.json'))
                if (final_meta.get('sourceFingerprint') != source_hash
                        or final_meta.get('sourceBlendSha256') != blend_hash
                        or final_meta.get('regions') != receipts
                        or final_meta.get('rendered') is not True):
                    raise ValueError('Completed image has stale provenance.')
                validate_machine(output.with_suffix('.machine.json'), scene, view, quality)
                saved = image_data(output, settings['resolution'])
                del saved
                expected_chunks = color_chunks(tile_dir / f"{specs[0]['id']}.png")
                if color_chunks(output) != expected_chunks:
                    raise ValueError('Completed image colour chunks differ from its regions.')
                manifest.update(complete=True)
                manifest.pop('lastError', None)
                persist('complete')
                print(f'CHECKPOINT {scene}/{view}: verified complete image and all region receipts; no work repeated.', flush=True)
                return
            except (OSError, ValueError, KeyError):
                pass
        persist('assembling')
        print(f'CHECKPOINT {scene}/{view}: assembling central uint16 pixels; no blending.', flush=True)
        png = assemble(output, receipts, settings['resolution'])
        unchanged()
        meta = read_json(verify_file(build['metadata']))
        meta.update(rendered=True, bytes=png['bytes'], sha256=png['sha256'], renderMethod=METHOD,
                    sourceFingerprint=source_hash, sourceBlendSha256=blend_hash,
                    regions=receipts, overscanPixels=OVERSCAN, coreGrid=[COLS, ROWS],
                    construction=build, assembledAt=now(),
                    colorMetadata=png['colorChunks'],
                    elapsedSeconds=machine['elapsedSeconds'])
        atomic_json(output.with_suffix('.json'), meta)
        # The construction .machine.json remains untouched until this point.
        atomic_json(output.with_suffix('.machine.json'), machine)
        manifest.update(complete=True, full={'png': png, 'blend': file_receipt(blend),
                        'metadata': file_receipt(output.with_suffix('.json')),
                        'machine': file_receipt(output.with_suffix('.machine.json'))})
        manifest.pop('lastError', None)
        persist('complete')
        print(f'CHECKPOINT {scene}/{view}: complete {output} ({png["bytes"]} bytes).', flush=True)
    except BaseException as error:
        manifest.update(complete=False, lastError=f'{type(error).__name__}: {error}')
        persist('interrupted' if isinstance(error, KeyboardInterrupt) else 'failed')
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene', choices=SCENES)
    parser.add_argument('--view', choices=VIEWS)
    parser.add_argument('--quality', choices=('draft', 'final'), default='final')
    parser.add_argument('--samples', type=int, help='Explicit sample override, fingerprinted in checkpoints.')
    args = parser.parse_args()
    if args.samples is not None and args.samples < 1:
        parser.error('--samples must be positive')
    # Fail before any Blender process starts if the assembly dependencies are missing.
    import cv2
    import numpy
    print(f'CHECKPOINT assembly runtime: OpenCV {cv2.__version__}; NumPy {numpy.__version__}', flush=True)
    with queue_lock():
        jobs = [(scene, view) for scene in ((args.scene,) if args.scene else SCENES)
                for view in ((args.view,) if args.view else VIEWS)]
        queue_path = OUTPUT / 'final-queue.json'
        state = {'startedAt': now(), 'pid': os.getpid(), 'method': METHOD,
                 'quality': args.quality, 'requestedJobs': [
                     {'scene': scene, 'view': view} for scene, view in jobs],
                 'complete': False, 'failed': False, 'jobs': [],
                 'current': {'scene': jobs[0][0], 'view': jobs[0][1]}}
        atomic_json(queue_path, state)
        try:
            for scene, view in jobs:
                checkpoint = OUTPUT / 'checkpoints' / f'{scene}-{view}'
                if args.quality != 'final':
                    checkpoint = checkpoint / args.quality
                state.update(current={'scene': scene, 'view': view,
                                      'manifest': relative(checkpoint / 'manifest.json')},
                             updatedAt=now())
                atomic_json(queue_path, state)
                render_job(scene, view, args)
                manifest = read_json(checkpoint / 'manifest.json')
                if manifest.get('complete') is not True:
                    raise RuntimeError(f'{scene}/{view} returned without a complete checkpoint.')
                state['jobs'].append({'scene': scene, 'view': view, 'complete': True,
                                      'retainedRegionCount': len(manifest.get('tiles', {})),
                                      'manifest': relative(checkpoint / 'manifest.json')})
                state.update(current=None, updatedAt=now())
                atomic_json(queue_path, state)
            state.update(complete=True, finishedAt=now())
            atomic_json(queue_path, state)
        except BaseException as error:
            state.update(complete=False, failed=True, current=None,
                         error=f'{type(error).__name__}: {error}', finishedAt=now())
            atomic_json(queue_path, state)
            raise


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('CHECKPOINT interrupted; resume the same command to verify/reuse completed regions.', file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f'CHECKPOINT stopped: {error}', file=sys.stderr)
        raise SystemExit(1)
