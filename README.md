# The Missing Scratch

**Can a vision model tell when moving one obstacle leaves a camera target uninspected?**

The Missing Scratch is an Innodata Track 2 benchmark for reflected camera coverage. A seeded generator produces top-down images, questions, and reference answers for three inspection decisions. Each matched pair changes one element of the layout and flips the correct answer.

**200 scenes · 100 matched pairs · 3 task types · 2 geometry methods**

[Example pair](#example-pair) · [Quick start](#quick-start) · [Frozen dataset](datasets/v4/cases.json) · [Evidence and results](#evidence-and-results)

## Problem statement

A camera can have a mirror in view while the target's reflected path is blocked. A false coverage answer could lead an inspector to mark a hidden target as checked. The benchmark asks models to determine whether the target is visible, identify the first obstruction along the reflected route, or choose the change that restores coverage.

## Example pair

| Obstacle in the reflected path | Obstacle moved clear of the path |
| --- | --- |
| ![Top-down benchmark diagram, case 0000-0](datasets/v4/images/0000-0.png) | ![Top-down benchmark diagram, case 0000-1](datasets/v4/images/0000-1.png) |
| **0000-0 · Blocked** | **0000-1 · Visible** |

The camera, target, and mirror stay fixed. Obstacle A changes position. The diagrams are the exact images shipped in the benchmark.

## Quick start

Clone the repository, then run these commands from its root. The release check requires Python 3.12 or later and uses the standard library. The Docker demo requires Docker Compose.

```sh
python3 -m scratch.verify_release
docker compose up --build
```

Open [the local playground](http://127.0.0.1:8000/#inspection). Predict both scenes, reveal the verified ray, or open the simulator and choose a loading dock, warehouse aisle, or inspection cell. Each site offers visibility, first-obstruction, and repair practice. The simulator reveals a laser-style ray that stops at the first obstruction. Its equipment is illustrated and its practice cases are separate from benchmark evaluation. The frozen `datasets/v4/` directory is the source for comparable model runs.

For generation and tests without Docker:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make test
make build
```

## How the pipeline works

| Stage | Entry point | Output |
| --- | --- | --- |
| Generate | `python -m scratch.build --seed 42 --pairs 100` | PNGs, questions, choices, geometry traces, and reference answers |
| Check geometry | `scratch/geometry.py` | Exact-fraction virtual-target and equal-slope calculations, with separate occlusion checks |
| Verify release | `python3 -m scratch.verify_release` | Checks image hashes, pair structure, and evidence binding against the shipped manifest |
| Reproduce | `python3 -m scratch.reproduce datasets/v4 --revision ab5b79d` | Clean Linux ARM64 Docker comparison of the manifest and all 200 images |
| Evaluate | `python -m scratch.evaluate` | Per-case responses in vision or question-only mode |
| Report | `python -m scratch.publish_reports` | Run summaries, task and difficulty breakdowns, strict pair accuracy, and paired error examples |

The frozen release has **68 visibility, 66 obstruction, and 66 repair cases**. Both members of a pair must be correct to earn pair credit.

## Evidence and results

| Evidence | Status | Inspect |
| --- | --- | --- |
| Frozen dataset | 200 images and 100 pairs checked | [Manifest](datasets/v4/cases.json) · [Images](datasets/v4/images) |
| Clean rebuild | Manifest and all 200 images matched byte for byte on Linux ARM64 | [Rebuild record](site/reproduction.json) |
| Shortcut audit | Measured on held-out layouts. Visibility position rules scored 34/68. Camera-side-only scored 38/66 on obstruction and 36/66 on repair. | [Audit output](datasets/v4/validity-audit.json) |
| Blind human review | 72-case workflow ready. Agreement pending independent reviews. | [Review protocol](evidence/RUNBOOK.md#collect-the-evidence) |
| Frontier model comparison | Report pipeline verified. Full vision and question-only runs pending. | [Published aggregates](site/model-reports.json) · [API setup](docs/API-SETUP.md) |
| Physical camera check | Capture protocol ready. Actual camera observations pending. | [Demo protocol](evidence/DEMO.md) |

The synthetic geometry assumes a single finite specular mirror, a point camera and target, and opaque obstacles in a top-down plane. Difficulty labels are generator settings. The shortcut audit covers specific simple features. Blind review will test whether people can interpret the diagrams as intended.

## Documentation

[Evidence runbook](evidence/RUNBOOK.md) · [System card](evidence/SYSTEM.md) · [Judging checklist](evidence/JUDGING.md) · [Product requirements](docs/PRD.md) · [Technical design](docs/TRD.md) · [Development lifecycle](docs/SDLC.md)

The public playground reveals reference answers. Use the separate blind packet for human review. Keep provider keys, raw review files, and the coordinator key outside the public repo. Model icons are from [Lobe Icons](https://github.com/lobehub/lobe-icons).
