"""Fetch the exact CC0 photographic maps used by the local world renderer.

The packed architecture-world.blend does not need this download. Run this script
only to rebuild the procedural world with tools/render-world.py.
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'assets' / 'source' / 'texture-manifest.json'
DESTINATION = ROOT / 'assets' / 'source' / 'textures'
USED_ASSET_IDS = (
    'fine_grained_wood', 'rosewood_veneer1', 'marble_01',
    'plastered_wall', 'rough_linen', 'concrete_wall_004',
    'kloofendal_48d_partly_cloudy',
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verified(path, record):
    return (path.is_file() and path.stat().st_size == record['bytes']
            and sha256(path) == record['sha256'].lower())


def fetch(record):
    rel = Path(record['file'])
    if rel.is_absolute() or '..' in rel.parts:
        raise ValueError(f'Unsafe manifest path: {rel}')
    target = (DESTINATION / rel).resolve()
    target.relative_to(DESTINATION.resolve())
    url = urllib.parse.urlparse(record['url'])
    if url.scheme != 'https' or url.hostname != 'dl.polyhaven.org':
        raise ValueError(f'Unexpected download origin: {record["url"]}')
    if verified(target, record):
        print(f'Verified existing {rel}')
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.download')
    for attempt in range(3):
        try:
            request = urllib.request.Request(record['url'], headers={
                'User-Agent': 'ArchitectureWorldSourceFetcher/1.0'
            })
            with urllib.request.urlopen(request, timeout=90) as response:
                redirect = urllib.parse.urlparse(response.geturl())
                if redirect.scheme != 'https' or redirect.hostname != 'dl.polyhaven.org':
                    raise ValueError('Download redirected outside the recorded asset host')
                with temporary.open('wb') as output:
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        total += len(chunk)
                        if total > record['bytes']:
                            raise ValueError(f'Asset exceeds recorded size: {rel}')
                        output.write(chunk)
            if not verified(temporary, record):
                raise ValueError(f'SHA-256 or byte-size verification failed: {rel}')
            os.replace(temporary, target)
            print(f'Downloaded and verified {rel}')
            return
        except Exception:
            temporary.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    assets = {item['id']: item for item in manifest['assets']}
    missing = set(USED_ASSET_IDS) - assets.keys()
    if missing:
        raise ValueError(f'Manifest is missing required assets: {sorted(missing)}')
    selected = [assets[asset_id] for asset_id in USED_ASSET_IDS]
    for asset in selected:
        for record in asset['files']:
            fetch(record)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    (DESTINATION / 'manifest.json').write_text(json.dumps({
        'license': manifest['license'], 'licenseUrl': manifest['licenseUrl'],
        'assets': selected,
    }, indent=2) + '\n', encoding='utf-8')
    print('All six texture sets and the final Kloofendal HDRI are verified.')


if __name__ == '__main__':
    main()
