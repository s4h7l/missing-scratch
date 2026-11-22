"""Run three selected vision systems in both conditions on one reviewed manifest."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .evaluate import PROVIDER_KEYS
from .publish_reports import report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--gemini', required=True, help='Exact Gemini vision model ID')
    p.add_argument('--claude', required=True, help='Exact Claude vision model ID')
    p.add_argument('--groq', required=True, help='Exact vision model ID on Groq')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true', help='Run all six batches, consuming provider quota')
    args = p.parse_args()
    systems = [('gemini',args.gemini), ('anthropic',args.claude), ('groq',args.groq)]
    missing = [PROVIDER_KEYS[provider] for provider,_ in systems if not os.environ.get(PROVIDER_KEYS[provider])]
    cases = len(json.loads(args.dataset.read_bytes())['cases'])
    calls = cases*len(systems)*2
    print(f'Plan: {cases} cases × 3 systems × 2 modes = up to {calls} requests.', flush=True)
    if missing:
        p.exit(2, 'Set the missing environment variables: ' + ', '.join(missing) + '\n')
    if not args.execute:
        return

    args.out.mkdir(parents=True,exist_ok=False)
    logs = []
    for provider,model in systems:
        for mode in ('vision','question-only'):
            path = args.out/f'{provider}-{mode}.jsonl'
            subprocess.run([sys.executable,'-m','scratch.evaluate','--dataset',str(args.dataset),
                            '--provider',provider,'--model',model,'--mode',mode,
                            '--record',str(path),'--max-requests',str(cases)],check=True)
            try:
                report(args.dataset,[path])
            except ValueError as exc:
                p.exit(2,f'Stopped at {path}: {exc}\n')
            logs.append(path)
    (args.out/'aggregate.json').write_text(json.dumps(report(args.dataset,logs),indent=2)+'\n')


if __name__ == '__main__':
    main()
