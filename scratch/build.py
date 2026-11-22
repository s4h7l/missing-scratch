"""Generate paired visual questions, exact answer keys and the static judge site."""
import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from .geometry import checked

ROOT = Path(__file__).resolve().parents[1]


def panel(draw, scene, oy, heading):
    def point(p):
        return round(40 + p[0]*6), round(oy+212-p[1]*6)

    draw.rounded_rectangle((12,oy+6,667,oy+237), 12, fill='#101c29')
    draw.text((30,oy+20), heading, fill='#ffffff', font_size=20)
    for i in range(10,101,10):
        a,b = point((i,0)),point((i,24))
        draw.line([a,b], fill='#26394a')
    draw.line([point((0,0)),point((100,0))], fill='#53697b', width=2)
    l,r = scene['mirror']
    draw.line([point((l,0)),point((r,0))], fill='#71eaec',width=6)
    draw.text((point((l,0))[0],oy+214),'Mirror',fill='#71eaec',font_size=13)
    for name,(x,y,u,v) in scene['blocks'].items():
        draw.rectangle([point((x,v)),point((u,y))],fill='#f6a860')
        px,py=point((u,v))
        draw.text((px+4,py),name,fill='#ffcfaa',font_size=15)
    for key,color in [('camera','#75d0ff'),('target','#ddf58b')]:
        x,y=point(scene[key])
        draw.ellipse((x-6,y-6,x+6,y+6),fill=color)
        draw.text((x+9,y-16),key.title(),fill=color,font_size=16)


def render(scene, variants, file):
    im=Image.new('RGB',(680, 248*(1+len(variants))), '#08101a')
    draw=ImageDraw.Draw(im)
    panel(draw,scene,0,'Base scene')
    for i,(name,variant) in enumerate(variants,1):
        panel(draw,variant,i*248,name)
    im.save(file)


def generate(seed, pairs, out):
    rng = random.Random(seed)
    images = out/'images'
    images.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i in range(pairs):
        dx = rng.randint(-5,5)
        y = rng.randint(16,24)
        difficulty = ('easy','medium','hard')[i%3]
        clutter = dict(list({'C':(10+dx,4,13+dx,7),'D':(82+dx,4,85+dx,7)}.items())[:i%3])
        width=(13,9,6)[i%3]
        mirror=(50+dx-width+rng.randint(-2,2),50+dx+width+rng.randint(-2,2))
        height=rng.randint(6,9)
        # Place one obstacle on the incoming ray and one clear of it.
        middle = round(50 - 30*(height+2)/y)+dx
        a = (middle-4,height,middle+4,height+4)
        b = (middle-4,height+15,middle+4,height+19)
        for j in range(2):
            blocks={'A':a if j==0 else b,'B':b if j==0 else a,**clutter}
            scene={'camera':(20+dx,y),'target':(80+dx,y),'mirror':mirror,'blocks':blocks}
            kind=('visibility','blocker','repair')[(i//3)%3]
            variants=[]
            if kind=='visibility':
                blocks={'A':a if j==0 else b, 'B':(84+dx,11,88+dx,15), **clutter}
                scene['blocks']=blocks
                prompt='Can the camera see the marked target through the mirror?'
                options=['Visible','Blocked']
                correct=options[not checked(scene)[0]]
            elif kind=='blocker':
                incoming = a if j == 0 else b
                outgoing = (100+2*dx-a[2],a[1],100+2*dx-a[0],a[3])
                blocks={'A':incoming,'B':outgoing,**clutter}
                scene['blocks']=blocks
                prompt='Which obstacle would the ray from the camera encounter first along the mirror path?'
                options=list(blocks)
                hits=checked(scene)[1]
                if hits != (['A','B'] if j == 0 else ['B']):
                    raise ValueError(f'Unexpected blockers: {hits}')
                correct=hits[0]
            else:
                prompt='Which replacement scene restores visibility through the mirror?'
                options=['Move obstacle A','Move obstacle B']
                for name,block in zip(options,('A','B')):
                    changed={**blocks,block:(87+dx,10,90+dx,13)}
                    variants.append((name,{**scene,'blocks':changed}))
                answers=[name for name,variant in variants if checked(variant)[0]]
                if len(answers)!=1:
                    raise ValueError(f'Expected one valid repair: {answers}')
                correct=answers[0]
            if rng.randrange(2):
                options.reverse()
            case_id=f'{i:04d}-{j}'
            image=images/f'{case_id}.png'
            render(scene,variants,image)
            visible, blockers, x=checked(scene)
            rows.append(dict(id=case_id,pair=i,type=kind,difficulty=difficulty,
                question=prompt, options=options, answer=correct,
                image=f'images/{image.name}',image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                trace=dict(camera=scene['camera'],target=scene['target'],bounce=[float(x),0],
                           visible=visible,blockers=blockers)))
        if rows[-1]['answer']==rows[-2]['answer']:
            raise ValueError(f'Pair {i} did not flip')
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--pairs',type=int,default=100)
    parser.add_argument('--out',type=Path,default=Path('dist'))
    args=parser.parse_args()
    if not 9 <= args.pairs <= 1000:
        parser.error('Choose 9–1,000 pairs')
    args.out.mkdir(parents=True,exist_ok=True)
    for source in (ROOT/'site').iterdir():
        shutil.copyfile(source,args.out/source.name)
    rows=generate(args.seed,args.pairs,args.out)
    payload=json.dumps(dict(seed=args.seed,cases=rows),sort_keys=True,indent=2)
    (args.out/'cases.json').write_text(payload)
    print(f'{len(rows)} synthetic cases; manifest SHA256 {hashlib.sha256(payload.encode()).hexdigest()}')


if __name__=='__main__':
    main()
