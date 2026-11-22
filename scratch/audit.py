"""Measure the best in-sample position-only rules on rendered visibility diagrams."""
from collections import Counter
import hashlib
import json

from PIL import Image


def best_rule(points, axis):
    values = sorted({xy[axis] for xy, _ in points})
    counts = Counter((xy[axis], blocked) for xy, blocked in points)
    return max(sum(n for (coordinate, blocked), n in counts.items()
                   if ((low <= coordinate <= high) == polarity) == blocked)
               for low in values for high in values if low <= high
               for polarity in (False, True))


def held_out_rules(records):
    """Leave one complete camera-layout group out at a time."""
    groups = sorted({group for _, _, group in records})
    result = Counter()
    for group in groups:
        train = [(xy, label) for xy, label, g in records if g != group]
        test = [(xy, label) for xy, label, g in records if g == group]
        if not train:
            continue
        for axis, name in enumerate(('horizontal', 'vertical')):
            values = sorted({xy[axis] for xy, _ in train})
            rules = [(low, high, polarity) for low in values for high in values
                     if low <= high for polarity in (False, True)]

            def correct(rule, observations):
                low, high, polarity = rule
                return sum(((low <= xy[axis] <= high) == polarity) == label
                           for xy, label in observations)

            rule = max(rules, key=lambda rule: correct(rule, train))
            result[name] += correct(rule, test)
        counts = Counter(train)
        majority = sum(label for _, label in train) * 2 > len(train)
        for xy, label in test:
            blocked, visible = counts[xy, True], counts[xy, False]
            prediction = majority if blocked == visible else blocked > visible
            result['coordinate_lookup'] += prediction == label
        result['total'] += len(test)
    return dict(groups=len(groups), **result)


def categorical_checks(cases, features):
    result = {}
    for task in ('blocker', 'repair'):
        rows = [case for case in cases if case['type'] == task]
        groups = {case['layout_group'] for case in rows}
        rules = {
            'labeled_obstacles_only': lambda case: json.dumps(features[case['id']]['obstacles'], sort_keys=True),
            'answer_option_order_only': lambda case: tuple(case['options']),
            'camera_side_only': lambda case: case['trace']['camera'][0] < case['trace']['bounce'][0] - 20,
        }
        if task == 'repair':
            rules['image_panel_order_only'] = lambda case: tuple(features[case['id']]['panel_order'])
        scores = {}
        for name, feature in rules.items():
            correct = 0
            for group in groups:
                training = [c for c in rows if c['layout_group'] != group]
                majority = Counter(c['answer'] for c in training)
                if not majority:
                    continue
                for case in rows:
                    if case['layout_group'] != group:
                        continue
                    counts = Counter(c['answer'] for c in training if feature(c) == feature(case)) or majority
                    prediction = min(counts, key=lambda answer: (-counts[answer], answer))
                    correct += prediction == case['answer']
            scores[name] = correct
        result[task] = dict(held_out_groups=len(groups), total=len(rows), correct=scores)
    return result


def audit(cases, folder, manifest_bytes, features=None):
    records = []
    for case in cases:
        if case['type'] != 'visibility':
            continue
        with Image.open(folder/case['image']) as image:
            # Isolate the movable orange obstacle. The fixed orange rectangle is at the right.
            tile = image.crop((90, 0, 420, 248))
            rgb = tile.load()
            positions = [(x + 90,y) for y in range(tile.height) for x in range(tile.width)
                         if rgb[x,y] == (246,168,96)]
            xy = (min(x for x,_ in positions), min(y for _,y in positions))
            records.append((xy, case['answer'] == 'Blocked', case['layout_group']))
    points = [(xy, label) for xy, label, _ in records]
    by_position = Counter(points)
    ceiling = sum(max(by_position[xy,False], by_position[xy,True]) for xy in {xy for xy,_ in points})
    return dict(dataset=hashlib.sha256(manifest_bytes).hexdigest(), total=len(points),
                horizontal_interval_correct=best_rule(points,0),
                vertical_interval_correct=best_rule(points,1),
                coordinate_lookup_correct=ceiling, held_out=held_out_rules(records),
                other_tasks=categorical_checks(cases, features) if features else {})
