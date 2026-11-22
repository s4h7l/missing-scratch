# Innodata Track 2 submission gates

Working pitch now: **Can a vision model tell which surface a camera can inspect through a mirror? The Missing Scratch generates paired scenes and scores each answer against two geometry methods.** Add “we spot-checked [X] cases with a real camera” only after recording them.

| Hack2Skill criterion | Evidence to deliver |
|---|---|
| Implementation, 25% | Clean checkout or container builds and runs. A teammate independently regenerates the manifest and replays saved responses. |
| Validity, 25% | Two reviewers independently answer 50–100 exact images with the actual prompts and answer order. Publish reviewer agreement, per-reviewer agreement with the solver, and exclusions before freezing. Inspect text-only results for leakage. |
| Variation, 20% | Report denominators by task and configuration. Use matched answer flips and both-correct pair accuracy. Add true geometry variation and establish human difficulty before claiming difficulty effects. |
| Originality, 15% | Quantify two recurring errors, e.g. checking only the incoming path or accepting a change that leaves the ray obstructed. Include counts and paired case IDs. |
| Impact, 15% | Show an actual blind spot and two images where the answer flips. A false coverage claim can leave a marked surface uninspected. |

## Evidence collection
1. Export a blind packet to each reviewer. Lock replies before showing the answer keys. Preserve case IDs, review dates, agreement counts and adjudication. Freeze the final manifest before official runs.
2. Run three image-capable models and their question-only baselines on the same frozen manifest. Track provider, model ID, date, errors, output, task accuracy and strict pair accuracy. Compare simple chance separately.
3. Capture 5–10 physical cases across visible, obstructed and restored. For each case record setup photo, fixed camera frame, target, expected visibility, observed outcome and mismatch notes. Choose cases before shooting and retain mismatches.
4. Put the replay command, manifest hash, raw sanitized model replies, results table, blind report and selected physical frames in the submission. Keep the extra task family out until it can pass all the same checks.

## Reference interfaces reviewed
These are public benchmark interfaces, not a ranking of competing Innodata teams.

| Reference | What works | Opportunity for this project |
|---|---|---|
| [VisuLogic](https://visulogic-benchmark.github.io/VisuLogic/) | Human scores and breakdowns sit beside model results. | Pair scores with a case-level reveal and link each failure count to examples. |
| [Microsoft Research dynamic benchmark](https://www.microsoft.com/en-us/research/project/image-understanding-benchmark/) | The overview and task figure quickly explain procedural image generation. | Put an interactive task on the first screen and offer a reproducibility command. |
| [CVSBench](https://github.com/earth-insights/CVSBench) | Clear evaluation toolkit and documented output files. | Keep the prompt, diagram, paired case and proof together in the judge interface. |

## MCP servers, plugins, connectors and sites
- GitHub connector: repository and CI inspection once a destination exists. GitHub Actions runs CI and GitHub Pages can host the offline app.
- Postman plugin: useful when adding a judge API, especially for request debugging and contract checks. The current playground is static.
- Figma plugin: optional for design review. Current UI is in code.
- Chrome/browser tools: local visual and accessibility checks. Docker Desktop: container build and local hosting.
- OpenRouter, Gemini and OpenAI: direct evaluation APIs via the local runner. Store credentials in shell environment or approved secret storage.
- Optional publication: use GitHub Pages for the static demo and a dataset host only after review and freeze. No additional cloud connector is required for scoring.

Connected availability does not imply external accounts were linked or deployment was enabled.
