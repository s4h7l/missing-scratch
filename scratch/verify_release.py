"""Check the frozen manifest, matched pairs, image bytes, and evidence binding."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def verify(root, rebuild_record):
    manifest = (root / 'cases.json').read_bytes()
    digest = hashlib.sha256(manifest).hexdigest()
    data = json.loads(manifest)
    if json.loads((root / 'validity-audit.json').read_text())['dataset'] != digest:
        raise ValueError('Shortcut audit does not match the manifest')
    case_ids, images = set(), set()
    pairs = defaultdict(list)
    tasks = Counter()
    for case in data['cases']:
        case_id, image = case['id'], case['image']
        if case_id in case_ids or image in images or image != f'images/{case_id}.png':
            raise ValueError(f'Unexpected or duplicate case/image: {case_id}')
        if case['answer'] not in case['options']:
            raise ValueError(f'Reference answer is missing from choices: {case_id}')
        if hashlib.sha256((root / image).read_bytes()).hexdigest() != case['image_sha256']:
            raise ValueError(f'Image hash mismatch: {image}')
        pairs[case['pair']].append(case)
        case_ids.add(case_id)
        images.add(image)
        tasks[case['type']] += 1
    for pair, members in pairs.items():
        if len(members) != 2 or len({case['type'] for case in members}) != 1 or len({case['answer'] for case in members}) != 2:
            raise ValueError(f'Expected two members with the same task and different answers: {pair}')
    if {str(path.relative_to(root)) for path in (root / 'images').iterdir()} != images:
        raise ValueError('Image directory differs from the manifest')
    record = json.loads(rebuild_record.read_text())
    if record['manifest_sha256'] != digest or record['images_byte_identical'] != len(images):
        raise ValueError('Rebuild record does not match the shipped dataset')
    return dict(manifest_sha256=digest, seed=data['seed'], cases=len(case_ids), pairs=len(pairs), tasks=dict(tasks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path, nargs='?', default=Path('datasets/v4'))
    parser.add_argument('--rebuild-record', type=Path, default=Path('site/reproduction.json'))
    args = parser.parse_args()
    print(json.dumps(verify(args.dataset, args.rebuild_record), indent=2))


if __name__ == '__main__':
    main()
