"""Replay or record model responses on a frozen dataset."""
import argparse
from datetime import datetime, timezone
import base64
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_model(provider, model, case, folder, mode):
    from string import ascii_uppercase
    choices = case['options']
    prompt = case['question'] + '\n' + '\n'.join(
        f'{letter}. {choice}' for letter, choice in zip(ascii_uppercase, choices)
    ) + '\nReply with only the option letter.'
    encoded = None
    if mode == 'vision':
        image = (folder/case['image']).read_bytes()
        if hashlib.sha256(image).hexdigest() != case['image_sha256']:
            raise ValueError(f"Image changed for {case['id']}")
        encoded = base64.b64encode(image).decode()
    if provider == 'gemini':
        import re
        if not re.fullmatch(r'[a-zA-Z0-9_.-]+', model):
            raise ValueError('Invalid Gemini model ID')
        key = os.environ['GEMINI_API_KEY']
        endpoint = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        headers = {'x-goog-api-key':key}
        parts = [{'text':prompt}]
        if encoded:
            parts.append({'inline_data':{'mime_type':'image/png','data':encoded}})
        body = {'contents':[{'parts':parts}]}
    else:
        key_name, endpoint = {
            'openai':('OPENAI_API_KEY','https://api.openai.com/v1/chat/completions'),
            'openrouter':('OPENROUTER_API_KEY','https://openrouter.ai/api/v1/chat/completions'),
        }[provider]
        headers = {'Authorization':'Bearer '+os.environ[key_name]}
        content = [{'type':'text','text':prompt}]
        if encoded:
            content.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+encoded}})
        body = {'model':model,'messages':[{'role':'user','content':content}]}
    headers['Content-Type'] = 'application/json'
    with urlopen(Request(endpoint,data=json.dumps(body).encode(),headers=headers),timeout=90) as response:
        data = json.load(response)
    if provider == 'gemini':
        return ''.join(part.get('text','') for part in data['candidates'][0]['content']['parts'])
    return data['choices'][0]['message']['content'] or ''


def selected_option(case, reply):
    text = reply.get('response', '').strip().upper()
    allowed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[:len(case['options'])]
    return case['options'][allowed.index(text)] if len(text) == 1 and text in allowed else None


def metrics(cases, output):
    counts=defaultdict(lambda: [0,0])
    pairs=defaultdict(list)
    for case,reply in zip(cases,output):
        correct = selected_option(case, reply) == case['answer']
        for label in ('overall',case['type'],case['difficulty'],case['type']+'/'+case['difficulty']):
            counts[label][0] += int(correct)
            counts[label][1] += 1
        pairs[case['pair']].append(correct)
    both = [all(group) for group in pairs.values() if len(group)==2]
    counts['both_pair_members'] = [sum(both),len(both)]
    return {name:dict(correct=c,total=n,accuracy=c/n if n else None) for name,(c,n) in counts.items()}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',type=Path,default=Path('dist/cases.json'))
    parser.add_argument('--provider',choices=['openai','gemini','openrouter'])
    parser.add_argument('--model')
    parser.add_argument('--mode',choices=['vision','question-only'],default='vision')
    parser.add_argument('--max-requests',type=int)
    operation=parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--record',type=Path)
    operation.add_argument('--replay',type=Path)
    operation.add_argument('--chance',action='store_true')
    args=parser.parse_args()
    data=args.dataset.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    cases=json.loads(data)['cases']
    if args.record:
        if not args.provider or not args.model or not args.max_requests or args.max_requests<1:
            parser.error('Live runs require provider, model, and a positive request cap')
        key_name={'gemini':'GEMINI_API_KEY','openai':'OPENAI_API_KEY',
                  'openrouter':'OPENROUTER_API_KEY'}[args.provider]
        if not os.environ.get(key_name):
            parser.error(f'Set {key_name} before starting a live run')
        cases=cases[:args.max_requests]
        args.record.parent.mkdir(parents=True,exist_ok=True)
        with args.record.open('x') as log:
            log.write(json.dumps(dict(dataset=digest,provider=args.provider,model=args.model,mode=args.mode,recorded_at=datetime.now(timezone.utc).isoformat()))+'\n')
            output=[]
            for case in cases:
                result={'id':case['id']}
                try:
                    result['response']=request_model(args.provider,args.model,case,args.dataset.parent,args.mode)
                except (HTTPError,URLError,TimeoutError,KeyError,IndexError) as error:
                    result['error']=f'HTTP {error.code}' if isinstance(error,HTTPError) else type(error).__name__
                log.write(json.dumps(result)+'\n')
                log.flush()
                output.append(result)
                if result.get('error') in {'HTTP 401','HTTP 403','HTTP 402','HTTP 429'}:
                    break
    elif args.replay:
        metadata,*output=map(json.loads,args.replay.read_text().splitlines())
        if metadata['dataset']!=digest or [row['id'] for row in output]!=[c['id'] for c in cases[:len(output)]]:
            parser.error('Run does not match the dataset and case order')
    else:
        rng=random.Random(42)
        output=[{'response':chr(65+rng.randrange(len(case['options'])))} for case in cases]
    print(json.dumps(dict(source='synthetic chance baseline' if args.chance else 'model log',
                          dataset=digest,scored=len(output),errors=sum('error' in row for row in output),
                          metrics=metrics(cases,output)),indent=2))


if __name__=='__main__':
    main()
