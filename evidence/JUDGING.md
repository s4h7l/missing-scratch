# Track 2 judging checklist

Source: [Hack2Skill's Track 2 criteria](https://hack2skill.com/event/innodata/?sectionid=6aee108b9be15aea67016065). Weights are indicative.

| Criterion | Evidence available | Finish before submitting |
|---|---|---|
| Implementation · 25% | Seeded generator, exact manifest, Docker demo, reproducible scoring | Ask a teammate to reproduce the same Docker release from a clean checkout and record the hash |
| Validity · 25% | Two geometry methods, exact image checksums, obstacle height diagnostic | Have two reviewers independently complete the 72-case packet. Report agreement, ambiguities and any exclusions. Run question-only controls. Inspect additional image shortcuts, including horizontal position. |
| Variation · 20% | Three tasks and 100 pairs | Present specific examples of distinct reasoning. Treat the difficulty labels as generated settings until difficulty is measured. |
| Engineering judgment · 15% | Corrected a synthetic shortcut and measured the effect | Use three or more vision models and give failure counts, denominators and case examples. |
| Impact and communication · 15% | Paired judge challenge and live simulator | Show how false coverage can leave a target uninspected. Add 5–10 camera checks when recorded, including mismatches. |

## Measured design finding

In the original 68 visibility cases, a single threshold on the movable blocker's vertical position matched 68/68 labels. In v2, the moved obstacle stays at the same height in both cases. The same feature's best threshold matches 34/68, even when chosen on those cases. This measures one dataset shortcut. It does not measure model performance or rule out other shortcuts.

Freeze and distribute the v2 manifest and images together. Do not mix with earlier scores or reviewer packets.

## Finalist sequence

Show one coverage-changing pair and ask judges to commit both predictions. Reveal the trace. Show one recorded model mistake and its consequence if model runs have completed. Follow with the corresponding physical frames only once captured. Keep the Evidence page one click away for the manifest and diagnostic.

## Second-pass judge audit

The v2 visibility labels still separate perfectly on an in-sample interval of the movable obstacle's horizontal pixel coordinate (68/68). A single horizontal threshold scores 54/68. This is a diagnostic, not a generalization estimate. Do not present v2 as proof that a model reasons about optical geometry. Before freezing a competition dataset, counterbalance obstacle positions across diverse camera and target layouts so the same obstacle coordinate occurs with both labels, then rerun shortcut controls on held-out layout groups. Reissue the review packet and model reports against the new manifest.
