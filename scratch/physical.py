"""Summarize camera observations and retain mismatches with their photo references."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from PIL import Image


def summarize(file, plan=None):
    root = file.parent.resolve()
    rows = {}
    planned = None
    if plan is not None:
        with plan.open(newline='') as source:
            planned = {row['case_id']: row['expected_visibility'] for row in csv.DictReader(source)}
    with file.open(newline='') as source:
        for line, row in enumerate(csv.DictReader(source), 2):
            case = row['case_id'].strip()
            expected = row['expected_visibility'].strip().lower()
            observed = row['observed_visibility'].strip().lower()
            if not case or case in rows or {expected, observed} - {'visible', 'blocked'}:
                raise ValueError(f'Row {line}: need a unique case and two visibility labels')
            if planned is not None and planned.get(case) != expected:
                raise ValueError(f'Row {line}: case or expected visibility differs from the capture plan')
            if not row['capture_date'].strip() or not row['target'].strip():
                raise ValueError(f'Row {line}: date and target are required')
            photo_hashes = {}
            for key in ('setup_photo', 'camera_frame'):
                path = (root / row[key]).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError(f'Row {line}: missing local {key}')
                with Image.open(path) as image:
                    image.verify()
                photo_hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            if expected != observed and not row['mismatch_notes'].strip():
                raise ValueError(f'Row {line}: add mismatch notes')
            rows[case] = dict(row, match=expected == observed, photo_sha256=photo_hashes)
    return dict(total=len(rows), matches=sum(row['match'] for row in rows.values()),
                mismatches=[row for row in rows.values() if not row['match']],
                cases=list(rows.values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('--plan', type=Path, help='Unedited capture-plan CSV with pre-recorded predictions')
    args = parser.parse_args()
    report = summarize(args.csv, args.plan)
    if not 5 <= report['total'] <= 10:
        parser.error('Record 5–10 camera cases before producing a validation summary')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
