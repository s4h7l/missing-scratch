"""Export exact benchmark inputs with opaque IDs and a separate coordinator key."""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random


def select_cases(cases, count, seed):
    rng = random.Random(seed)
    pairs = defaultdict(list)
    for case in cases:
        pairs[case['pair']].append(case)
    if count is None:
        selected = list(cases)
    else:
        if not 1 <= count <= len(pairs):
            raise ValueError('Case count must be between 1 and the number of pairs')
        strata = defaultdict(list)
        for pair in pairs.values():
            case = rng.choice(pair)
            strata[case['type'], case['difficulty']].append(case)
        for group in strata.values():
            rng.shuffle(group)
        selected = []
        while len(selected) < count:
            for key in sorted(strata):
                if strata[key] and len(selected) < count:
                    selected.append(strata[key].pop())
    rng.shuffle(selected)
    return selected


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, default=Path('dist/cases.json'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--count', type=int, help='Sample this many cases, at most one from each pair')
    p.add_argument('--seed', type=int, default=73)
    args = p.parse_args()
    data = args.dataset.read_bytes()
    cases = select_cases(json.loads(data)['cases'], args.count, args.seed)
    key_path = args.out.with_name(args.out.name + '-private-key.json')
    if key_path.exists():
        p.error('Coordinator key already exists. Choose a new output name.')
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/'images').mkdir()
    mapping = {}
    with (args.out/'review.csv').open('w', newline='') as f:
        out = csv.writer(f)
        out.writerow(['case_id','image','question','choices A onward','reviewer answer letter','ambiguity notes'])
        for i, case in enumerate(cases, 1):
            code = f'R{i:03d}'
            image = f'images/{code}.png'
            source = (args.dataset.parent/case['image']).read_bytes()
            if hashlib.sha256(source).hexdigest() != case['image_sha256']:
                raise ValueError(f"Image hash mismatch for {case['id']}")
            (args.out/image).write_bytes(source)
            out.writerow([code, image, case['question'], ' | '.join(case['options']), '', ''])
            mapping[code] = case['id']
    key_path.write_text(json.dumps(dict(dataset=hashlib.sha256(data).hexdigest(), cases=mapping), indent=2)+'\n')
    print(f'{len(cases)} cases. Coordinator key stored separately: {key_path}')


if __name__ == '__main__':
    main()
