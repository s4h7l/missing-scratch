"""Publish aggregate scores for complete runs on exactly the served manifest."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from .evaluate import PROVIDER_KEYS, metrics, selected_option


FAILURES = {
    'False coverage': 'An inspector could assume a hidden target was checked.',
    'Missed coverage': 'An inspector could repeat a check that the camera can already perform.',
    'Wrong obstruction': 'An inspector could move the wrong obstacle.',
    'Wrong repair': 'A proposed adjustment could leave the target hidden.',
    'Invalid option': 'The response cannot be mapped to a benchmark choice.',
}


def failure_breakdown(cases, rows):
    counts = defaultdict(lambda: {'count': 0, 'examples': []})
    for case, row in zip(cases, rows, strict=True):
        prediction = selected_option(case, row)
        if prediction == case['answer']:
            continue
        if prediction is None:
            label = 'Invalid option'
        elif case['type'] == 'visibility':
            label = 'False coverage' if prediction == 'Visible' else 'Missed coverage'
        else:
            label = 'Wrong obstruction' if case['type'] == 'blocker' else 'Wrong repair'
        group = counts[label]
        group['count'] += 1
        if len(group['examples']) < 3:
            group['examples'].append(dict(case=case['id'], expected=case['answer'], predicted=prediction))
    return [dict(label=label, consequence=FAILURES[label], **counts[label])
            for label in FAILURES if label in counts]


def paired_findings(cases, rows):
    groups = defaultdict(list)
    for case, row in zip(cases, rows, strict=True):
        groups[case['pair']].append(dict(case=case['id'], task=case['type'],
                                        expected=case['answer'], predicted=selected_option(case, row)))
    total = exactly_one_correct = repeated_answer = 0
    example = None
    best_rank = 0
    for pair_id, members in groups.items():
        if len(members) != 2 or members[0]['expected'] == members[1]['expected']:
            continue
        total += 1
        exactly_one_correct += sum(member['expected'] == member['predicted'] for member in members) == 1
        if members[0]['predicted'] is None or members[0]['predicted'] != members[1]['predicted']:
            continue
        repeated_answer += 1
        task = members[0]['task']
        failure = {
            'visibility': 'False coverage' if members[0]['predicted'] == 'Visible' else 'Missed coverage',
            'blocker': 'Wrong obstruction',
            'repair': 'Wrong repair',
        }[task]
        rank = 2 if failure == 'False coverage' else 1
        if rank > best_rank:
            example = dict(pair=pair_id, cases=members, failure=failure, consequence=FAILURES[failure])
            best_rank = rank
    return dict(answer_flips=total, exactly_one_correct=exactly_one_correct,
                repeated_answer=repeated_answer, example=example)


def report(dataset, logs):
    data = dataset.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    cases = json.loads(data)['cases']
    expected = [case['id'] for case in cases]
    models = defaultdict(dict)
    for path in logs:
        meta, *rows = map(json.loads, path.read_text().splitlines())
        provider, name, mode = (meta.get(key) for key in ('provider', 'model', 'mode'))
        if (meta.get('dataset') != digest or provider not in PROVIDER_KEYS
                or not isinstance(name, str) or not name or mode not in {'vision', 'question-only'}
                or [row.get('id') for row in rows] != expected
                or any('error' in row or not isinstance(row.get('response'), str) for row in rows)):
            raise ValueError(f'{path}: expected a complete, error-free model log for this dataset')
        key = (provider, name)
        if mode in models[key]:
            raise ValueError(f'{path}: duplicate mode for {name}')
        models[key][mode] = dict(scores=metrics(cases, rows), failures=failure_breakdown(cases, rows),
                                 pairs=paired_findings(cases, rows),
                                 recorded_at=meta.get('recorded_at'))
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
