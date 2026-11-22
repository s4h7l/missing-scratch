"""Diagnostic for a simple single-feature shortcut in visibility diagrams."""
from collections import Counter
import hashlib
from pathlib import Path

from PIL import Image


def audit(cases, folder: Path, manifest_bytes: bytes):
    height_scores = Counter()
    visibility = [case for case in cases if case['type'] == 'visibility']
    for case in visibility:
        with Image.open(folder/case['image']) as image:
            # The large orange rectangle is the movable obstacle on the left half.
            left = image.crop((90, 0, 420, 248))
            top = next(y for y in range(left.height)
                       if sum(left.getpixel((x,y)) == (246,168,96)
                              for x in range(left.width)) >= 40)
            height_scores[top, case['answer']] += 1
    thresholds = sorted({y for y, _ in height_scores})
    correct = max(
        sum(n for (y, answer), n in height_scores.items()
            if ((y >= cut) == direction) == (answer == 'Blocked'))
        for cut in [*thresholds, thresholds[-1]+1] for direction in (False, True)
    )
    return dict(dataset=hashlib.sha256(manifest_bytes).hexdigest(),
                feature='Vertical position of the large left obstacle',
                best_threshold_correct=correct, total=len(visibility))
