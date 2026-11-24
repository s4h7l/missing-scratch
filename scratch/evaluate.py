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


CHAT_ENDPOINTS = {
    'openai': 'https://api.openai.com/v1/chat/completions',
    'openrouter': 'https://openrouter.ai/api/v1/chat/completions',
    'groq': 'https://api.groq.com/openai/v1/chat/completions',
}
PROVIDER_KEYS = {
    'openai': 'OPENAI_API_KEY',
    'openrouter': 'OPENROUTER_API_KEY',
    'groq': 'GROQ_API_KEY',
    'gemini': 'GEMINI_API_KEY',
    'anthropic': 'ANTHROPIC_API_KEY',
}


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
    elif provider == 'anthropic':
        endpoint = 'https://api.anthropic.com/v1/messages'
        headers = {'x-api-key': os.environ[PROVIDER_KEYS[provider]],
                   'anthropic-version': '2023-06-01'}
        content = []
        if encoded:
            content.append({'type': 'image', 'source': {
                'type': 'base64', 'media_type': 'image/png', 'data': encoded}})
        content.append({'type': 'text', 'text': prompt})
        body = {'model': model, 'max_tokens': 512,
                'messages': [{'role': 'user', 'content': content}]}
    else:
        key_name = PROVIDER_KEYS[provider]
        endpoint = CHAT_ENDPOINTS[provider]
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
    if provider == 'anthropic':
        return ''.join(part['text'] for part in data['content'] if part['type'] == 'text')
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
    parser.add_argument('--provider',choices=sorted(PROVIDER_KEYS))
    parser.add_argument('--model')
    parser.add_argument('--mode',choices=['vision','question-only'],default='vision')
    parser.add_argument('--max-requests',type=int,help='Maximum new provider requests')
    parser.add_argument('--resume-from',type=Path,help='Copy the successful prefix from a previous run into a new log')
    operation=parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--record',type=Path)
    operation.add_argument('--replay',type=Path)
    operation.add_argument('--chance',action='store_true')
    args=parser.parse_args()
    data=args.dataset.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    cases=json.loads(data)['cases']
    if args.resume_from and not args.record:
        parser.error('--resume-from requires --record with a fresh output path')
    if args.record:
        if not args.provider or not args.model or not args.max_requests or args.max_requests<1:
            parser.error('Live runs require provider, model, and a positive request cap')
        key_name = PROVIDER_KEYS[args.provider]
        if not os.environ.get(key_name):
            parser.error(f'Set {key_name} before starting a live run')
        identity = dict(dataset=digest,provider=args.provider,model=args.model,mode=args.mode)
        metadata = dict(identity,recorded_at=datetime.now(timezone.utc).isoformat())
        output = []
        if args.resume_from:
            try:
                previous, *rows = map(json.loads, args.resume_from.read_text().splitlines())
                if any(previous.get(key) != value for key,value in identity.items()):
                    raise ValueError('Previous run belongs to a different dataset, model or mode')
                if [row.get('id') for row in rows] != [case['id'] for case in cases[:len(rows)]]:
                    raise ValueError('Previous run does not match the frozen case order')
                for row in rows:
                    if 'error' in row or not isinstance(row.get('response'),str):
                        break
                    output.append(row)
                metadata['recorded_at'] = previous.get('recorded_at') or metadata['recorded_at']
            except (OSError, ValueError, AttributeError) as error:
                parser.error(str(error))
        remaining = cases[len(output):len(output)+args.max_requests]
        args.record.parent.mkdir(parents=True,exist_ok=True)
        with args.record.open('x') as log:
            log.write(json.dumps(metadata)+'\n')
            for row in output:
                log.write(json.dumps(row)+'\n')
            log.flush()
            for case in remaining:
                result={'id':case['id']}
                try:
                    result['response']=request_model(args.provider,args.model,case,args.dataset.parent,args.mode)
                except (HTTPError,URLError,TimeoutError,KeyError,IndexError) as error:
                    result['error']=f'HTTP {error.code}' if isinstance(error,HTTPError) else type(error).__name__
                log.write(json.dumps(result)+'\n')
                log.flush()
                output.append(result)
                if 'error' in result:
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
