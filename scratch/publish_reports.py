"""Publish aggregate scores for complete runs on exactly the served manifest."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from .evaluate import metrics


def report(dataset, logs):
    data = dataset.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    cases = json.loads(data)['cases']
    expected = [case['id'] for case in cases]
    models = defaultdict(dict)
    for path in logs:
        meta, *rows = map(json.loads, path.read_text().splitlines())
        provider, name, mode = (meta.get(key) for key in ('provider', 'model', 'mode'))
        if (meta.get('dataset') != digest or provider not in {'gemini', 'openai', 'openrouter'}
                or not isinstance(name, str) or not name or mode not in {'vision', 'question-only'}
                or [row.get('id') for row in rows] != expected
                or any('error' in row or not isinstance(row.get('response'), str) for row in rows)):
            raise ValueError(f'{path}: expected a complete, error-free model log for this dataset')
        key = (provider, name)
        if mode in models[key]:
            raise ValueError(f'{path}: duplicate mode for {name}')
        models[key][mode] = dict(scores=metrics(cases, rows), recorded_at=meta.get('recorded_at'))
    return dict(dataset=digest, reports=[
        dict(provider=provider, model=model, modes=modes)
        for (provider, model), modes in sorted(models.items())
    ])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, default=Path('dist/cases.json'))
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('logs', nargs='+', type=Path)
    args = parser.parse_args()
    payload = report(args.dataset, args.logs)
    temporary = args.out.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2) + '\n')
    temporary.replace(args.out)


if __name__ == '__main__':
    main()
