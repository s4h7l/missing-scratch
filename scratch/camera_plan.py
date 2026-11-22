"""Prepare a measured tabletop layout and predicted labels, without observations."""
import argparse
import copy
import csv
import json
from pathlib import Path

from .geometry import checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--replay', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    first, second = json.loads(args.replay.read_text())
    blocked, clear = first['scene'], second['scene']
    cases = [('01-pair-blocked', blocked), ('02-pair-clear', clear)]
    narrow = copy.deepcopy(clear)
    x = checked(clear)[2]
    left = int(x) + 3
    narrow['mirror'] = (left, left+7)
    cases.append(('03-mirror-miss', narrow))
    cases.append(('04-mirror-restored', clear))
    moved = copy.deepcopy(clear)
    moved['camera'][0] += 5
    cases.append(('05-camera-shift', moved))
    moved_blocked = {**moved, 'blocks': blocked['blocks']}
    cases.append(('06-shifted-with-blocker', moved_blocked))

    args.out.mkdir(parents=True, exist_ok=False)
    fields = ['case_id','capture_date','setup_photo','camera_frame','target',
              'expected_visibility','observed_visibility','match','mismatch_notes']
    note = ['# Tabletop capture card', '',
            'Use centimetres on a tabletop. The mirror lies along y=0 and faces into positive y. '
            'Measure from its reflective face. x runs along the mirror; y runs outward. '
            'Coordinate pairs below are in centimetres at half the diagram scale.', '',
            'Use a vertical mirror, hold camera height and aim steady within each pair, and keep target and blocker tall enough '
            'to cross the camera height. Place the camera lens at the listed point. Aim so the mirror is in frame. '
            'Judge whether the marked target is visible inside the mirror, even if it appears elsewhere in the frame.', '',
            'Save an overhead setup photo and an actual camera frame for each case. Inspect the mirror region independently '
            'before opening the expected-label CSV. Keep every mismatch. The generated labels are geometry predictions.', '',
            f'Stage example: synthetic cases {first["id"]} and {second["id"]}. Physical captures 01 and 02 reproduce their footprints.']
    with (args.out/'physical.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for case_id, scene in cases:
            visible, _, _ = checked(scene)
            writer.writerow(dict(case_id=case_id, target='marked target',
                                 expected_visibility='visible' if visible else 'blocked',
                                 setup_photo=f'{case_id}-setup.jpg', camera_frame=f'{case_id}-frame.jpg'))
            scaled = lambda coords: ', '.join(f'{n/2:g}' for n in coords)
            note.extend(['', f'## {case_id}', f'- Camera: ({scaled(scene["camera"])})',
                         f'- Target: ({scaled(scene["target"])})',
                         f'- Reflective mirror span on x: {scaled(scene["mirror"])}',
                         *[f'- Obstacle {name} footprint (x min, y min, x max, y max): {scaled(box)}'
                           for name, box in scene['blocks'].items()]])
    (args.out/'CAPTURE.md').write_text('\n'.join(note)+'\n')


if __name__ == '__main__':
    main()
