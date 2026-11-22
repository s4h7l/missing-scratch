import tempfile
import unittest
from pathlib import Path

from scratch.build import generate
from scratch.geometry import checked


class GeometryTests(unittest.TestCase):
    def test_ray(self):
        scene={'camera':(20,20),'target':(80,20),'mirror':(40,60),'blocks':{}}
        self.assertEqual(checked(scene),(True,[],50))
        scene['blocks']['A']=(32,9,38,11)
        self.assertEqual(checked(scene),(False,['A'],50))
        scene['mirror']=(51,60)
        self.assertEqual(checked(scene),(False,[],50))

    def test_reproducible_flip_and_coverage(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            a=generate(42,9,Path(first))
            b=generate(42,9,Path(second))
            self.assertEqual(a,b)
            self.assertEqual(len(a),18)
            self.assertEqual(len({(r['type'],r['difficulty']) for r in a}),9)
            for left,right in zip(a[::2],a[1::2]):
                self.assertNotEqual(left['answer'],right['answer'])
                self.assertNotEqual(left['image_sha256'],right['image_sha256'])
