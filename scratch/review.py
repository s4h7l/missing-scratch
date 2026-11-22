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
            answers[case_id]=row['reviewer answer letter'].strip().upper()
    return answers


def main():
    p=argparse.ArgumentParser()
    p.add_argument('reviewers',nargs=2,type=Path)
    p.add_argument('--dataset',type=Path,default=Path('dist/cases.json'))
    p.add_argument('--key',type=Path,help='Private coordinator key for opaque review IDs')
    args=p.parse_args()
    data=args.dataset.read_bytes()
    cases={case['id']:case for case in json.loads(data)['cases']}
    if args.key:
        key=json.loads(args.key.read_text())
        if key['dataset'] != hashlib.sha256(data).hexdigest():
            p.error('Coordinator key belongs to another dataset')
        cases={review_id:cases[case_id] for review_id,case_id in key['cases'].items()}
    left,right=[read_review(file,cases) for file in args.reviewers]
    report=dict(cases=len(cases),both_answered=0,reviewer_agreement=0,
                reviewer_a_matches=0,reviewer_b_matches=0,issues=[])
    for case_id,case in cases.items():
        a,b=left.get(case_id,''),right.get(case_id,'')
        letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'[:len(case['options'])]
        expected=letters[case['options'].index(case['answer'])]
        if len(a) == len(b) == 1 and a in letters and b in letters:
            report['both_answered']+=1
            report['reviewer_agreement']+=int(a==b)
            report['reviewer_a_matches']+=int(a==expected)
            report['reviewer_b_matches']+=int(b==expected)
        if a!=expected or b!=expected:
            report['issues'].append(dict(case=case_id,first=a,second=b,reference=expected))
    n=report['both_answered']
    report['agreement_rate']=report['reviewer_agreement']/n if n else None
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
