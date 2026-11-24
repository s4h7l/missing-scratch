# Case study · Gemini missed a visibility change

The frozen opening pair keeps the camera, target, and mirror fixed and shifts one obstacle. Gemini 3 Flash Preview answered **Blocked** for both images. It earned one scene point out of two and zero strict pair points out of one.

| Frozen case | Exact input | Verified answer | Gemini with image |
| --- | --- | --- | --- |
| 0000-0 | [Blocked layout](../datasets/v4/images/0000-0.png) | Blocked | Blocked |
| 0000-1 | [Clear layout](../datasets/v4/images/0000-1.png) | Visible | Blocked |

This error could lead an inspector to repeat an inspection that the camera could already perform through the mirror. This case study covers one clear scene in one measured pilot pair. It does not establish a failure rate across the benchmark. The [pilot record](../site/lab-pilot.json) binds replies to the frozen manifest and separates image from question-only inputs.

## What the shortcut checks found

The [frozen layout audit](../datasets/v4/validity-audit.json) holds out whole layout groups. The tested obstacle-position rules reached 34/68 on visibility. Obstacle labels and answer-option order reached 33/66 on obstruction and repair. The camera-side rule reached 38/66 on obstruction and 36/66 on repair, so residual cues deserve attention.

A separate leave-one-layout-group-out lookup used exact question text, then text plus ordered answer choices. For each held-out case it predicted the most frequent matching training label, falling back to the training majority if there was no match. Ties used alphabetical answer order. Both variants scored 34/68 for visibility and 33/66 each for obstruction and repair. These checks cover those simple lookup rules. Full model controls and measured difficulty comparisons are still pending.

The 72-case blind packet was checked against frozen v4. Its images, questions, and choice order matched the benchmark. Its response fields were empty and the coordinator key was absent. Independent reviewer agreement remains pending.
