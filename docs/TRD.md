# Missing Scratch | Technical Requirements Document

## Architecture

1. **Generator:** Python and Pillow produce PNGs and a sorted JSON manifest from seed 42 and 100 pair indices by default.
2. **Verification:** Unfold the target across the mirror and solve the reflected point. Independently find it by enforcing equal signed slopes to the normal. Occlusion uses segment clipping in the first method and edge intersections in the second. Use exact fractions through reference computation and reject disagreements before exporting.
3. **Interface:** Static HTML, CSS and JavaScript. A Go service in Docker serves the offline app. The simulator produces illustrative layouts in the browser; these use numerical geometry and never enter the frozen benchmark or its model results.
4. **Evaluation:** Server-side CLI sends the same prompt and choices across providers. Vision mode also sends the exact PNG; question-only mode omits it. Validate the PNG hash when sending it.
5. **Publication:** Logs have provider, exact model ID, dataset hash, mode and timestamp. The exporter checks full case order, manifest identity and provider error status, then publishes aggregate metrics and limited case IDs for each failure category. The browser checks the report hash against the served manifest.

## Data and scoring

The manifest records the case ID, pair ID, task, difficulty configuration, question, options, reference answer, image path and SHA-256, and a geometry trace. Repair uses one image with multiple panels and exactly one valid listed adjustment. Each example is scored from a single option letter; invalid responses score incorrect. Pair accuracy counts both correct against the denominator of complete pairs. Case-level publication publishes expected and selected options, not raw provider text.

## Constraints and reproducibility

The target and camera are points in an ideal 2D scene with one finite horizontal mirror and opaque rectangles. There is no lens model, glare, or camera calibration. Difficulty labels describe generator settings rather than a calibrated difficulty curve. PNG bytes can vary across platforms; freeze a generated bundle and use it for every comparison. Blind reviewers must receive the separate answer-free export.

## Runtime and security

Pillow is pinned; Docker builders are pinned by digest. The final image runs a non-root static server with a read-only filesystem under Compose. No provider secrets belong in assets, HTML, Git or reports. CI scans dependencies and the runtime image. The browser can display only previously published aggregate data; provider calls are authorized and capped in the local runner.

## Evidence collection

False coverage can leave a target uninspected. A wrong blocker can send an operator to the wrong obstacle. A wrong repair can leave the same blind spot after adjustment. The exporter counts and names examples of each pattern. These are possible consequences until real runs establish which patterns actually occurred.
