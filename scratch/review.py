"""Summarize two independent blind reviews against a frozen dataset."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def read_review(file, ids):
    answers={}
    with file.open(newline='') as source:
        for row in csv.DictReader(source):
            case_id=row['case_id']
            if case_id not in ids or case_id in answers:
                raise ValueError(f'Unknown or duplicate case: {case_id}')
            answers[case_id]=(row['reviewer answer letter'].strip().upper(), row.get('ambiguity notes', '').strip())
    return answers


def main():
    p=argparse.ArgumentParser()
    p.add_argument('reviewers',nargs=2,type=Path)
    p.add_argument('--dataset',type=Path,default=Path('dist/cases.json'))
    p.add_argument('--require-complete', action='store_true')
    p.add_argument('--key',type=Path,help='Private coordinator key for opaque review IDs')
    args=p.parse_args()
    data=args.dataset.read_bytes()
    cases={case['id']:case for case in json.loads(data)['cases']}
    if args.key:
        key=json.loads(args.key.read_text())
        if key['dataset'] != hashlib.sha256(data).hexdigest():
            p.error('Coordinator key belongs to another dataset')
        cases={review_id:cases[case_id] for review_id,case_id in key['cases'].items()}
    if args.reviewers[0].resolve() == args.reviewers[1].resolve():
        p.error('Provide distinct reviewer files')
    left,right=[read_review(file,cases) for file in args.reviewers]
    report=dict(cases=len(cases),both_answered=0,reviewer_agreement=0,
                reviewer_a_matches=0,reviewer_b_matches=0,issues=[])
    for case_id,case in cases.items():
        a,note_a=left.get(case_id,('',''))
        b,note_b=right.get(case_id,('',''))
        letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'[:len(case['options'])]
        expected=letters[case['options'].index(case['answer'])]
        if len(a) == len(b) == 1 and a in letters and b in letters:
            report['both_answered']+=1
            report['reviewer_agreement']+=int(a==b)
            report['reviewer_a_matches']+=int(a==expected)
            report['reviewer_b_matches']+=int(b==expected)
        if a != expected or b != expected or note_a or note_b:
            report['issues'].append(dict(case=case_id, benchmark_case=case['id'], first=a,
                                         second=b, reference=expected, notes=[note_a,note_b]))
    n=report['both_answered']
    report['agreement_rate']=report['reviewer_agreement']/n if n else None
    report['dataset']=hashlib.sha256(data).hexdigest()
    print(json.dumps(report,indent=2))
    if args.require_complete and n != len(cases):
        p.exit(2, 'Both reviewers must answer every sampled case.\n')


if __name__=='__main__':
    main()
