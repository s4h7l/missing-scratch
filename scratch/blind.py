"""Export the exact images and shuffled-choice questions without answer metadata."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import random


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',type=Path,default=Path('dist/cases.json'))
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    cases=json.loads(args.dataset.read_text())['cases']
    random.Random(73).shuffle(cases)
    args.out.mkdir(parents=True,exist_ok=False)
    (args.out/'images').mkdir()
    with (args.out/'review.csv').open('w',newline='') as f:
        out=csv.writer(f)
        out.writerow(['case_id','image','question','choices A onward','reviewer answer letter','ambiguity notes'])
        for case in cases:
            shutil.copyfile(args.dataset.parent/case['image'],args.out/case['image'])
            out.writerow([case['id'],case['image'],case['question'],' | '.join(case['options']),'',''])


if __name__=='__main__':
    main()
