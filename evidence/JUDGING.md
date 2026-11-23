# Track 2 judging checklist

Source: [Hack2Skill's Track 2 criteria](https://hack2skill.com/event/innodata/?sectionid=6aee108b9be15aea67016065). Weights are indicative.

| Criterion | Evidence available | Finish before submitting |
|---|---|---|
| Implementation · 25% | Seeded generator, exact manifest, Docker demo, reproducible scoring. The [clean rebuild](../site/reproduction.json) matched the v4 manifest and all 200 images. | Have a teammate repeat the rebuild and record their result. |
| Validity · 25% | Two geometry methods, exact image checksums, and held-out shortcut checks for all three tasks | Have two reviewers independently complete the 72-case packet. Report agreement, ambiguities and any exclusions. Run question-only controls. |
| Variation · 20% | Three tasks and 100 pairs. The report computes task-by-difficulty scores for both model modes. | Treat the difficulty labels as generated settings until measured results show how performance changes. |
| Engineering judgment · 15% | Corrected a synthetic shortcut and measured the effect. The report surfaces both diagrams when a model repeats an answer across an answer-changing pair. | Run three vision models and their question-only controls. Verify the example and publish counts and denominators. |
| Impact and communication · 15% | Paired judge challenge and live simulator | Show how false coverage can leave a target uninspected. Add 5–10 camera checks when recorded, including mismatches. |

## Measured design finding

In the original 68 visibility cases, a single threshold on the movable blocker's vertical position matched 68/68 labels. In v2, the moved obstacle stays at the same height in both cases. The same feature's best threshold matches 34/68, even when chosen on those cases. This measures one dataset shortcut. It does not measure model performance or rule out other shortcuts.

The following notes document earlier dataset versions. Use the v4 manifest and matching review packet for the current evaluation.

## Finalist sequence

Show one coverage-changing pair and ask judges to commit both predictions. Reveal the trace. Show one recorded model mistake and its consequence if model runs have completed. Follow with the corresponding physical frames only once captured. Keep the Evidence page one click away for the manifest and diagnostic.

## Second-pass judge audit

The v2 visibility labels still separate perfectly on an in-sample interval of the movable obstacle's horizontal pixel coordinate (68/68). A single horizontal threshold scores 54/68. This is a diagnostic, not a generalization estimate. Do not present v2 as proof that a model reasons about optical geometry. Before freezing a competition dataset, counterbalance obstacle positions across diverse camera and target layouts so the same obstacle coordinate occurs with both labels, then rerun shortcut controls on held-out layout groups. Reissue the review packet and model reports against the new manifest.

## v3 counterbalance

Visibility pairs now occur in layout groups of two. Each group keeps two obstacle placements fixed and changes which placement intersects the ray by changing camera and target coordinates. A best-fit position-only interval and exact coordinate lookup both score 34/68 on the default dataset. This is an in-sample shortcut diagnostic for visibility, not a claim about other features, task types, or model performance. Review and evaluate v3 only. Before running models, check the other task families and test additional baselines with whole layout groups held out.

## v4 obstruction and repair checks

In both tasks the two cases share the labeled obstacles and answer option order. The intervention moves the camera. Repair also keeps the alternatives in the same panel order. The tested labeled-obstacle, option-order and repair panel-order rules each scored 33/66 on held-out pairs. The tested camera-side-only rule scored 38/66 for obstruction and 36/66 for repair, so residual predictive cues remain possible. This is a synthetic design diagnostic. Blind review and three real image-versus-text model comparisons are still required before final claims.
