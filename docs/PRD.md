# Missing Scratch | Product Requirements Document

**Purpose:** Help a judge or benchmark engineer determine whether vision models notice a change in camera coverage. The inspection application illustrates why an incorrect “visible” prediction matters: an obstructed target could be counted as inspected.

## Users and journeys

| User | Job | Journey |
|---|---|---|
| Judge | Understand and reproduce the claim | Open Overview → compare a blocked and visible pair → record both predictions → reveal the ray and compare outcomes |
| Benchmark engineer | Run a fair comparison | Freeze the dataset → run each model with and without images → replay the records and publish aggregate metrics |
| Blind reviewer | Check that the image supports its label | Receive the image and question packet → answer independently → return completed CSV before reading the key |
| Camera reviewer | Check limited real-world transfer | Capture a representative physical scene and compare the observed frame with its geometric prediction |

## Scope and acceptance

- **Dataset:** 200 image/question/reference-answer cases in 100 pairs covering visibility, obstructions and repair. Both geometry methods must agree, and each registered pair must flip its answer.
- **Demo:** Generate a fresh simulated layout, predict visibility, evaluate, and reveal the path. The fixed challenge has Previous and Next controls and reveals reference answers after both predictions.
- **Results:** Compare at least three image-capable models on identical frozen cases. Publish vision, question-only, per-task and strict pair accuracy with denominators. Record provider failures separately. A report must match the served manifest.
- **Evidence:** Record blind agreement on 50–100 cases and adjudication, and 5–10 physical cases with matches and mismatches. Keep both records distinct from mathematical validation.
- **Access:** Fast local demo, keyboard-accessible controls, reduced-motion support, named model marks, and visible loading and pending states.
- **Non-goals:** Live CCTV integration, field-of-view calibration, multi-mirror scenes, and guaranteed competition placement.

## Release criteria

A reviewer can regenerate the fixed dataset, confirm its manifest hash, run the browser demo, and replay a complete recorded model log. The submission may describe physical testing and model failures only after that evidence is recorded. Report depth and judge usability take priority over adding task families.
