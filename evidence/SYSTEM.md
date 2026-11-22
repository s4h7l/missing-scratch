# System card

**Purpose.** Measure whether image-capable models distinguish reflected inspection coverage, first obstructions, and repairs in controlled paired diagrams.

**Pipeline.** Seed → synthetic scene → two geometry methods → image and reference manifest → private provider logs → manifest-verified aggregate reports. The site and Docker runtime receive only the static presentation, synthetic cases and published aggregates.

**Score rules.** Accuracy uses the exact option selected. Pair accuracy counts both conditions together. Question-only repeats the same prompt and choices without the image. Publish exact provider IDs and compare the same manifest. Report failed or incomplete runs separately before attaching an official score.

**Limits.** A single ideal horizontal mirror, opaque rectangles, a point camera and a point target. The rendered scenes do not model lens field of view, glare or calibration. The landing page switches between two actual synthetic cases from the deterministic benchmark generator. Human review and camera captures are separate evidence sources and are currently pending.

**Repository reference.** [Spotlight, 1st place in its 2026 AI4Good problem case](https://github.com/ericgdevs/2026-AI4Good-Hackathon), grounds its README in a concrete need, distinguishes held-out measurements, and links a system card and limitations. Missing Scratch follows that evidence structure.
