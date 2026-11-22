"""Measure the best in-sample position-only rules on rendered visibility diagrams."""
from collections import Counter
import hashlib

from PIL import Image


def best_rule(points, axis):
    values = sorted({xy[axis] for xy, _ in points})
    counts = Counter((xy[axis], blocked) for xy, blocked in points)
    return max(sum(n for (coordinate, blocked), n in counts.items()
                   if ((low <= coordinate <= high) == polarity) == blocked)
               for low in values for high in values if low <= high
               for polarity in (False, True))


def audit(cases, folder, manifest_bytes):
    points = []
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
            points.append((xy, case['answer'] == 'Blocked'))
    by_position = Counter(points)
    ceiling = sum(max(by_position[xy,False], by_position[xy,True]) for xy in {xy for xy,_ in points})
    return dict(dataset=hashlib.sha256(manifest_bytes).hexdigest(), total=len(points),
                horizontal_interval_correct=best_rule(points,0),
                vertical_interval_correct=best_rule(points,1),
                coordinate_lookup_correct=ceiling)
