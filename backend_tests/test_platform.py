import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

from backend.db import store
from backend.services import benchmark, datasets, physical, providers, review
from backend.services.common import Problem, digest, rows


class OfflinePlatform(unittest.TestCase):
    def test_corrected_suite_review_camera_gate_and_replay(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(store, "RUNTIME_DIR", Path(temp)):
            store.initialize()
            suite = datasets.build("corrected", 100, 0)
            self.assertEqual((suite["tasks"], suite["pairs"], suite["layouts"]), (200, 100, 20))
            pack = datasets.export(suite["dataset_id"])
            with ZipFile(BytesIO(pack)) as z:
                manifest = [json.loads(line) for line in z.read("tasks.jsonl").decode().splitlines()]
                self.assertEqual(len(manifest), 200)
                self.assertNotIn("answer", manifest[0])
                self.assertEqual(z.read("manifest.sha256").decode().strip(), suite["manifest_sha256"])
            self.assertEqual(datasets.build("corrected", 100, 0), suite)
            self.assertEqual(datasets.export(suite["dataset_id"]), pack)

            cases = rows("SELECT id,kind,answer,pair,digest,question,options FROM cases WHERE dataset=? ORDER BY position",
                         (suite["dataset_id"],))
            self.assertEqual({r["kind"] for r in cases}, {"visibility", "obstruction", "repair"})
            with self.assertRaises(Problem) as gate:
                benchmark.check_gate(suite["dataset_id"])
            self.assertEqual(gate.exception.status, 409)

            review_id = review.create(suite["dataset_id"], 72)["review_id"]
            maps = json.loads(rows("SELECT maps FROM reviews WHERE id=?", (review_id,))[0]["maps"])
            for reviewer_id in review.REVIEWERS:
                responses = [{"code": code, "answer": rows("SELECT answer FROM cases WHERE id=?", (cid,))[0]["answer"],
                              "evidence": "marked X compared with reflected path", "ambiguity": "", "confidence": 5}
                             for code, cid in maps[reviewer_id].items()]
                review.submit(review_id, reviewer_id, responses)
            sealed = review.report(review_id)
            self.assertEqual(sealed["state"], "sealed")
            self.assertEqual(sealed["reviewers"]["R1"]["correct"], 72)
            self.assertEqual(sealed["reviewers"]["R2"]["correct"], 72)
            self.assertEqual(review.adjudicate(review_id, True, "Original sheets independently compared.")["accepted"], True)

            picked = []
            for kind, need in (("visibility", 2), ("obstruction", 2), ("repair", 1)):
                picked.extend(rows("SELECT id FROM cases WHERE dataset=? AND kind=? LIMIT ?",
                                   (suite["dataset_id"], kind, need)))
            truth_by_id = {r["id"]:r["answer"] for r in cases}
            for case_index,item in enumerate(picked):
                cid = item["id"]
                expected = physical.stages(cid)
                measurements = {name: physical.dimensions(trial["scene"]) for name, trial in expected.items()}
                calibration = physical.calibrate(cid, {"task_id":cid,"observer":"operator","trial":"fixture-1",
                    "scale_bar_mm":50,"mirror_width_mm":62,"lens_height_mm":30,"target_height_mm":30,
                    "measurements":measurements})
                for idx, (stage, trial) in enumerate(expected.items()):
                    pixel = case_index*8+idx
                    output = BytesIO()
                    Image.new("RGB", (128, 128), (pixel, 70, 120)).save(output, "PNG")
                    observation = "YES" if trial["solver_checks"][0]["visible"] else "NO"
                    physical.capture(cid, calibration["calibration_sha256"], stage, "R1", observation, output.getvalue())
                self.assertEqual(physical.status(cid)["state"], "complete_agrees", truth_by_id[cid])
            self.assertTrue(physical.summary(suite["dataset_id"])["gate_passed"])
            with patch.dict("os.environ", {"MS_OPENAI_MODELS":"fixture-model","OPENAI_API_KEY":""}), self.assertRaises(Problem) as no_key:
                benchmark.start(suite["dataset_id"], "openai", "fixture-model", "vision")
            self.assertEqual(no_key.exception.status, 503)

            synthetic_records = []
            for case in cases:
                options = json.loads(case["options"])
                synthetic_records.append({"task_id":case["id"],"image_sha256":case["digest"],
                    "prompt_sha256":digest(providers.prompt(case["question"],options)),
                    "status":"ok","raw":case["answer"],"metadata":{"fixture":"offline replay test"}})
            source_report = {"dataset_id":suite["dataset_id"],"manifest_sha256":suite["manifest_sha256"],
                "provider":"openai","model":"fixture-model","mode":"vision",
                "settings":benchmark.settings(512),"records":synthetic_records}
            replayed = benchmark.replay(source_report)
            self.assertEqual((replayed["state"],replayed["correct"],replayed["assigned"],
                              replayed["strict_pairs_correct"],replayed["pairs"]),
                             ("complete",200,200,100,100))
            exported = benchmark.export_run(replayed["run_id"])
            self.assertEqual(benchmark.replay(exported)["correct"],200)


if __name__ == "__main__":
    unittest.main()
