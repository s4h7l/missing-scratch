"""Build a committed snapshot and verify its dataset against a frozen release."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
from tempfile import TemporaryDirectory
from uuid import uuid4


def verify_dataset(reference, reproduced):
    manifest = (reference / 'cases.json').read_bytes()
    if manifest != (reproduced / 'cases.json').read_bytes():
        raise ValueError('Rebuilt manifest differs from the frozen release')
    cases = json.loads(manifest)['cases']
    for case in cases:
        image = case['image']
        rebuilt = (reproduced / image).read_bytes()
        if (hashlib.sha256(rebuilt).hexdigest() != case['image_sha256']
                or rebuilt != (reference / image).read_bytes()):
            raise ValueError(f'Image differs from the frozen release: {image}')
    return dict(manifest_sha256=hashlib.sha256(manifest).hexdigest(),
                images_byte_identical=len({case['image'] for case in cases}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path, help='Directory containing frozen cases.json and images')
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--platform', default='linux/arm64')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.revision + '^{commit}'],
                                       text=True).strip()
    archive = subprocess.check_output(['git', 'archive', revision])
    with TemporaryDirectory(prefix='missing-scratch-reproduction-') as directory:
        root = Path(directory)
        source = root / 'source'
        with tarfile.open(fileobj=io.BytesIO(archive)) as snapshot:
            snapshot.extractall(source, filter='data')
        image_tag = 'missing-scratch:reproduction-' + uuid4().hex
        subprocess.run(['docker', 'build', '--no-cache', '--platform', args.platform,
                        '-t', image_tag, str(source)], check=True)
        try:
            container = subprocess.check_output(['docker', 'create', image_tag], text=True).strip()
            try:
                reproduced = root / 'rebuilt'
                subprocess.run(['docker', 'cp', f'{container}:/public', str(reproduced)], check=True)
                result = verify_dataset(args.reference, reproduced)
            finally:
                subprocess.run(['docker', 'rm', container], check=True, capture_output=True)
        finally:
            subprocess.run(['docker', 'image', 'rm', image_tag], check=True, capture_output=True)
    print(json.dumps(dict(revision=revision, platform=args.platform, build_cache=False, **result), indent=2))


if __name__ == '__main__':
    main()
