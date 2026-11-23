import tempfile
import unittest
from dataclasses import replace
from io import BytesIO
from math import pi
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from backend.core.factory import generate_pair
from backend.core.geometry import Disk, Point, Scene, verify
from backend.db import store
from backend.schemas.tasks import PublicTask, RevealResponse
from backend.services.task_service import prepare


class OpticalRegressions(unittest.TestCase):
    def test_finite_mirror_and_two_ray_legs(self):
        scene = Scene(Point(0, 4), Point(8, 4), Point(0, 0), Point(8, 0),
                      Point(0, 1), -pi/4, pi/2)
        for altered, reason in [
            (scene, "clear"),
            (replace(scene, mirror_end=Point(3, 0)), "outside_finite_mirror"),
            (replace(scene, camera_heading=pi/2), "outside_camera_fov"),
            (replace(scene, reflective_normal=Point(0, -1)), "camera_on_nonreflective_side"),
            (replace(scene, blockers=(Disk("B", Point(2, 2), 0.5),)), "blocked"),
            (replace(scene, blockers=(Disk("B", Point(6, 2), 0.5),)), "blocked"),
        ]:
            for check in verify(altered):
                self.assertEqual(check.reason, reason)
                if check.hit:
                    self.assertAlmostEqual(check.hit.x, 4)
                    self.assertAlmostEqual(check.hit.y, 0)

    def test_paired_answers_and_controls(self):
        for kind in ("visibility", "obstruction", "repair"):
            answers = set()
            for seed in range(40):
                first, second = generate_pair(kind, seed)
                self.assertNotEqual(first.answer, second.answer)
                a, b = first.base.scene, second.base.scene
                if kind == "repair":
                    self.assertEqual(replace(a, camera_heading=b.camera_heading), b)
                else:
                    self.assertEqual(replace(a, mirror_start=b.mirror_start, mirror_end=b.mirror_end,
                                             reflective_normal=b.reflective_normal), b)
                for task in (first, second):
                    answers.add(task.answer)
                    if kind != "visibility":
                        self.assertFalse(task.base.visible)
                        self.assertEqual([k for k, c in task.alternatives.items() if c.visible], [task.answer])
            self.assertEqual(answers, set(first.options))


class PersistenceAndDiagrams(unittest.TestCase):
    def test_pair_commit_and_prediction_gate(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(store, "RUNTIME_DIR", Path(temp)):
            store.initialize()
            for kind in ("visibility", "obstruction", "repair"):
                tasks = generate_pair(kind, 42)
                records = [prepare(t, kind) for t in tasks]
                store.save_batch(records)
                for task, (pub, priv, img, reveal) in zip(tasks, records):
                    self.assertEqual(PublicTask(**pub).model_dump(), store.metadata(task.task_id))
                    self.assertEqual(set(pub), {"task_id","kind","question","image_url","options","difficulty","pair_id"})
                    evidence = priv["evidence"]
                    self.assertEqual(RevealResponse(task_id=task.task_id, ground_truth=task.answer,
                                                    prediction=task.answer, correct=True, evidence=evidence).correct, True)
                    self.assertEqual(store.image_bytes(task.task_id), img)
                    self.assertNotEqual(img, reveal)
                    with Image.open(BytesIO(img)) as image:
                        image.verify()
                    self.assertIsNone(store.locked_prediction("visitor", task.task_id, kind))
                    self.assertTrue(store.save_prediction("visitor", task.task_id, task.answer))
                    self.assertTrue(store.save_prediction("visitor", task.task_id, task.answer))
                    wrong = next(o for o in task.options if o != task.answer)
                    self.assertFalse(store.save_prediction("visitor", task.task_id, wrong))
                    if task == tasks[0]:
                        self.assertIsNone(store.locked_prediction("visitor", task.task_id, kind))
                for task in tasks:
                    self.assertEqual(store.locked_prediction("visitor", task.task_id, kind), task.answer)
                    self.assertIsNone(store.locked_prediction("other", task.task_id, kind))
                    self.assertEqual(store.metadata(task.task_id, private=True)["answer"], task.answer)


if __name__ == "__main__":
    unittest.main()
