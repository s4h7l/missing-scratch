# The Missing Scratch
An inspection coverage benchmark for Innodata Track 2. Given a top-down diagram, predict whether a camera can see a target through one finite mirror, identify the first obstruction, or pick a replacement scene that restores visibility.

## Start
Python 3.14, Pillow, HTML/CSS/JavaScript, a Go standard library static server in Docker, Docker Compose, GitHub Actions and GitHub Pages. No frontend package manager or database.

Linux/macOS (from this folder):
```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make test
make serve
```
Open http://127.0.0.1:8000. Alternatively run `docker compose up --build` on port 8000. Use only one server at a time. For official cross-machine comparisons, freeze one manifest and its PNGs from the same runtime and distribute that bundle. With Docker running, use `make freeze-docker` to export the exact served bundle, and pass `--dataset runs/frozen-200-v4/cases.json` to blind review and evaluation commands.

## Reproduce
`make build` rebuilds 200 cases from seed 42. For another destination use `.venv/bin/python -m scratch.build --seed 42 --pairs 100 --out /tmp/missing-scratch-replay`. Compare the manifest and image hashes using the same Python, Pillow and platform, or inside the same container build. The public judge site contains answer keys for the reveal. Distribute the separate blind packet for human review.

```sh
.venv/bin/python -m scratch.blind --count 72 --out runs/review-packet
.venv/bin/python -m scratch.review --key runs/review-packet-private-key.json runs/reviewer-a.csv runs/reviewer-b.csv
.venv/bin/python -m scratch.evaluate --chance
.venv/bin/python -m scratch.evaluate --replay runs/model-vision.jsonl
```

For a live run, set the appropriate API key in your shell (OPENAI_API_KEY, GEMINI_API_KEY or OPENROUTER_API_KEY). Supply an accessible model ID. Every live request may incur provider charges.

```sh
.venv/bin/python -m scratch.evaluate --provider openrouter --model YOUR_MODEL_ID --mode vision --max-requests 200 --record runs/model-vision.jsonl
```

Repeat for three distinct models and with `--mode question-only` using distinct files. Final runs must cover the same frozen IDs. Reports include denominators, transport errors, accuracy by task and difficulty, and strict both-correct pair accuracy. Inspect errors before comparing models. A partial or failed run is not a final benchmark. The offline judge site has no model credentials or live endpoint.

## What the geometry covers
The ideal diagram assumes a point camera, point target, a top-down horizontal specular mirror, a single reflected path, and opaque axis-aligned obstacles. The virtual-target construction and equal-slope construction use exact fractions. Segment-box clipping and geometric edge intersection check occlusion separately. These methods share assumptions and do not establish that the images are unambiguous to people. The starter uses obstacle shifts for visibility and blocker pairs, and swaps the two obstacle positions for repair pairs. Difficulty buckets use obstacle count and mirror width as design knobs, not measured difficulty. Rotating mirrors, calibrated camera FOV and a difficulty curve remain extensions.

## Evidence status
- Synthetic benchmark and local offline judge playground implemented.
- Blind human review, provider model evaluations, and physical camera evidence pending.
- No published deployment. GitHub Actions CI and manually triggered GitHub Pages workflows are provided. Enable Pages via GitHub Actions in the repository after the destination is chosen. Only the offline judge site belongs on Pages.
- See [submission plan](evidence/PLAN.md) for acceptance gates and service choices.

## Publish measured results

Keep credentials in your shell or secret manager. See `.env.example` for variable names. Use an image-capable Claude or Qwen model through the OpenRouter provider. Run the same cases in both modes, using distinct log files.

```sh
.venv/bin/python -m scratch.publish_reports --dataset runs/frozen-200-v4/cases.json \
  --out site/model-reports.json runs/model-vision.jsonl runs/model-text.jsonl
docker compose up --build -d
```

Only aggregate, complete logs tied to the exact served manifest appear on the site. Use the same frozen runtime for generation and serving. The report exporter rejects mismatched dataset hashes, partial logs, and provider errors. Raw responses and credentials stay outside tracked files. Model icons are from [Lobe Icons](https://github.com/lobehub/lobe-icons), with brand rights retained by their respective owners.

[System card](evidence/SYSTEM.md) · [Finalist demo protocol](evidence/DEMO.md) · [Evidence plan](evidence/PLAN.md)

## Product and engineering documentation

- [Product requirements (PRD)](docs/PRD.md)
- [Software development life cycle (SDLC)](docs/SDLC.md)
- [Technical requirements (TRD)](docs/TRD.md)

In the Simulator, **Generate a trial** creates a fresh layout. Predict visibility to grade it and reveal the ray. These practice trials are separate from fixed benchmark scores.

[Model API setup](docs/API-SETUP.md) covers Gemini, GroqCloud, Claude Platform, OpenAI, OpenRouter, and separate Codex CLI authentication.

[Track 2 judging checklist and shortcut audit](evidence/JUDGING.md). The v4 freeze replaces the earlier dataset. Send reviewers the opaque-ID packet and keep the coordinator key private.

[Evidence runbook](evidence/RUNBOOK.md) covers the held-out audit, review handoff, model runs, and physical check summaries.

The frozen v4 data reproduced byte for byte in a clean Linux ARM64 Docker build of the committed generator. [Rebuild record](site/reproduction.json) includes the commit and manifest hash. The runbook has the command for a second operator to repeat the check.
