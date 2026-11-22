# Missing Scratch | Software Development Life Cycle

| Stage | Owner role | Gate |
|---|---|---|
| Define | Product lead | Agree on the task definitions, scoring rules, supported geometry and evidence limits. |
| Design | Geometry and UX leads | Review both geometry methods, figure legibility, repair criteria and the judge flow. |
| Build | Engineering | Generate PNGs and a manifest from a seed. Keep credentials and private run files outside the static site. |
| Verify | Teammate or reviewer | Replay a fresh build in the same runtime, compare hashes, run CI, and exercise the simulator and paired reveal. Record failures. |
| Validate | Human and camera reviewers | Blind-answer exact inputs, resolve disagreements, and record representative real camera matches and mismatches. Freeze labels before final API runs. |
| Evaluate | Benchmark lead | Run comparable vision and text baselines, retain exact model IDs and logs, and replay scores. Investigate false visibility claims, wrong blockers and ineffective repairs. |
| Release | Maintainer | Review CI/audit output, approve aggregates and evidence, then publish the static site from an approved revision. |
| Maintain | Maintainer | Rebuild on changes, rerun geometry and scans, refresh reports only against a matching manifest, and retain the previous release for rollback. |

## Change and rollback

Changing seeds, scene geometry, images, question text, or answer order invalidates existing reports for the new dataset. Treat label changes as a new dataset. Keep the previous manifest, private evidence and Git revision so a release can be recreated. Restore the prior revision and report bundle to roll back. A new browser animation alone does not require re-running models when the manifest is identical.

## Current release state

The synthetic pipeline, judge UI, report exporter and private repository exist. Human review, physical camera validation and credentialed model runs require separate completion. CI executes geometry checks, deterministic rebuild comparison, dependency audit and a container image scan.
