"""Generate paired visual questions, exact answer keys and the static judge site."""
import argparse
import hashlib
import json
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from .audit import audit
from .geometry import checked, clip, edges

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


def generate(seed, pairs, out, replay=None, diagnostic=None):
    rng = random.Random(seed)
    images = out/'images'
    images.mkdir(parents=True,exist_ok=True)
    rows=[]
    visibility_index = 0
    layout_rng = random.Random(f"{seed}:visibility-v3")
    assignment_rng = random.Random(f'{seed}:label-assignment')
    label_orders = {}
    for index, task in enumerate(('blocker','repair'), 1):
        count = sum((i//3)%3 == index for i in range(pairs))
        label_orders[task] = [bool(i%2) for i in range(count)]
        assignment_rng.shuffle(label_orders[task])
    for i in range(pairs):
        difficulty = ('easy','medium','hard')[i%3]
        kind=('visibility','blocker','repair')[(i//3)%3]
        if kind != 'visibility':
            shift = rng.randint(-4, 4)
            height = rng.randint(7, 9)
            cameras = [(rng.randint(15, 19)+shift, 22), (rng.randint(39, 43)+shift, 22)]
            target = (rng.randint(80, 84)+shift, 22)
            mirror = (42+shift, 70+shift)
            labels = ['B','A'] if label_orders[kind].pop() else ['A','B']
            reverse_panels = bool(rng.randrange(2))
            obstacles = {}
            for label, (camera_x, _) in zip(labels, cameras):
                bounce = (camera_x + target[0]) / 2
                x = round(bounce + (camera_x-bounce)*(height+2)/22)
                obstacles[label] = (x-3, height, x+3, height+4)
            if kind == 'blocker' and i%3:
                obstacles['C'] = (70+shift, 2, 76+shift, 20)
            if i%3 == 2:
                obstacles['D' if kind=='blocker' else 'C'] = (6+shift,4,9+shift,8)
            obstacles = dict(sorted(obstacles.items()))
        if kind == 'visibility':
            if visibility_index % 2 == 0:
                center = 50 + layout_rng.randint(-5, 5)
                y_visible = layout_rng.randint(21, 24)
                low = layout_rng.randint(15, 20)
                high = layout_rng.randint(39, 43)
                height_visible = layout_rng.randint(7, 9)
                half_width = layout_rng.randint(6, 11)
            camera_x = low if visibility_index % 2 == 0 else high
            visibility_index += 1
            # Both absolute rectangles occur once blocked and once clear across a layout group.
            positions = []
            for offset in (low, high):
                x = center + round((offset - 50) * (height_visible + 2) / y_visible)
                positions.append((x-3,height_visible,x+3,height_visible+4))
            if camera_x == high:
                positions.reverse()
            visible_camera = (center+camera_x-50,y_visible)
            visible_target = (2*center-visible_camera[0],y_visible)
        reverse_choices = bool(rng.randrange(2))
        for j in range(2):
            variants=[]
            if kind != 'visibility':
                scene={'camera':cameras[j], 'target':target, 'mirror':mirror, 'blocks':obstacles}
            if kind=='visibility':
                scene = dict(camera=visible_camera, target=visible_target,
                             mirror=(center-half_width,center+half_width),
                             blocks={'A':positions[j], 'B':(86,11,90,15)})
                if checked(scene)[0] != (j == 1):
                    raise ValueError('Counterbalanced visibility case disagrees with design')
                prompt='Can the camera see the marked target through the mirror?'
                options=['Visible','Blocked']
                correct=options[not checked(scene)[0]]
            elif kind=='blocker':
                prompt='Which obstacle would the ray from the camera encounter first along the mirror path?'
                options=list(obstacles)
                hits=checked(scene)[1]
                correct=labels[j]
                if correct not in hits or labels[1-j] in hits:
                    raise ValueError(f'Unexpected blocker configuration: {hits}')
                # In dense cases C lies on the outgoing leg; the designated
                # blocker is on the incoming leg and is always met first.
                if 'C' in hits:
                    bounce = (checked(scene)[2],0)
                    if any(intersect(scene['camera'],bounce,obstacles['C']) for intersect in (clip,edges)):
                        raise ValueError('Secondary obstacle must be after the mirror')
                without_c = {**scene, 'blocks':{name:box for name,box in obstacles.items() if name != 'C'}}
                if checked(without_c)[1] != [correct]:
                    raise ValueError('Unexpected incoming obstacle')
            else:
                prompt='Which replacement scene restores visibility through the mirror?'
                options=['Move obstacle A','Move obstacle B']
                if reverse_panels:
                    options.reverse()
                for name in options:
                    block = name[-1]
                    changed={**obstacles,block:(91,8,95,12)}
                    variants.append((name,{**scene,'blocks':changed}))
                answers=[name for name,variant in variants if checked(variant)[0]]
                if len(answers)!=1:
                    raise ValueError(f'Expected one valid repair: {answers}')
                correct=answers[0]
            if reverse_choices:
                options.reverse()
            case_id=f'{i:04d}-{j}'
            image=images/f'{case_id}.png'
            render(scene,variants,image)
            visible, blockers, x=checked(scene)
            if diagnostic is not None:
                diagnostic[case_id] = dict(obstacles=scene['blocks'], panel_order=[name for name,_ in variants])
            if replay is not None and i == 0:
                replay.append(dict(id=case_id, scene=scene, visible=visible, bounce=float(x)))
            rows.append(dict(id=case_id,pair=i,type=kind,difficulty=difficulty,
                question=prompt, options=options, answer=correct,
                layout_group=(f'visibility-{(visibility_index-1)//2:03d}' if kind=='visibility' else f'{kind}-{i:03d}'),
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
    replay=[]
    diagnostic={}
    rows=generate(args.seed,args.pairs,args.out,replay,diagnostic)
    payload=json.dumps(dict(seed=args.seed,cases=rows),sort_keys=True,indent=2)
    (args.out/'cases.json').write_text(payload)
    (args.out/'replay.json').write_text(json.dumps(replay, indent=2)+'\n')
    (args.out/'validity-audit.json').write_text(json.dumps(audit(rows, args.out, payload.encode(), diagnostic), indent=2)+'\n')
    print(f'{len(rows)} synthetic cases; manifest SHA256 {hashlib.sha256(payload.encode()).hexdigest()}')


if __name__=='__main__':
    main()
