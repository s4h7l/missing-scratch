# Evidence runbook

Use the frozen Docker v3 manifest throughout. Each report must bind to its SHA-256.

1. **Shortcut diagnostic.** Open Evidence → Download diagnostic. Each visibility fold holds out both camera layouts and their paired images. Interval rules are fit on the remaining groups. Exact coordinate lookup uses the training majority for ties and unseen positions. The audit covers only the movable obstacle's position. It is neither a test of all visual shortcuts nor a model result.
2. **Blind review.** Give the same answer-free packet to two different reviewers. Ask each to complete the CSV independently and note ambiguous diagrams. Keep the coordinator key offline. Run the command below once both are back. Retain disagreements and notes. Adjudicate before final model requests. If any cases or labels change, create a new manifest and regenerate the packet; previous scores no longer attach to it.
3. **Models.** Use one vision-capable Gemini, one Claude, and a third image-capable model such as Qwen via Groq. Get each exact model ID from the account you're using. For each, run the same 200 cases once in vision mode and once in question-only mode. Save separate logs, then publish aggregates. The exporter rejects incomplete or mismatched logs. Report both-correct pair accuracy and show a real example of the most consequential failure observed.
4. **Physical checks.** Tape the tabletop positions, fix camera height and aim, and verify the target is outside the direct view for reflected checks. Record the prediction before looking at the live camera view. Photograph each setup and save the corresponding camera frame. Pick 5–10 cases spanning clear, obstructed, and restored paths. Capture the pair used on stage. Report setup limitations, calibration deviations and every mismatch. Keep private footage outside public assets unless cleared.

```sh
.venv/bin/python -m scratch.review --require-complete \
  --dataset runs/frozen-200-v3/cases.json \
  --key runs/judge-review-72-v3-private-key.json \
  runs/reviewer-a.csv runs/reviewer-b.csv > runs/human-review.json

# Repeat with the available exact model ID and both modes for each provider.
.venv/bin/python -m scratch.evaluate --dataset runs/frozen-200-v3/cases.json \
  --provider gemini --model YOUR_MODEL_ID --mode vision \
  --max-requests 200 --record runs/gemini-vision.jsonl

# Explicitly name the completed official logs. Do not include smoke logs.
.venv/bin/python -m scratch.publish_reports --dataset runs/frozen-200-v3/cases.json \
  --out site/model-reports.json runs/gemini-vision.jsonl runs/gemini-question-only.jsonl \
  runs/claude-vision.jsonl runs/claude-question-only.jsonl \
  runs/third-model-vision.jsonl runs/third-model-question-only.jsonl

cp evidence/physical-template.csv runs/physical.csv
# Fill the sheet and store photo references relative to runs/physical.csv.
.venv/bin/python -m scratch.physical runs/physical.csv > runs/physical-report.json
```

## Finalist demo

Play the synthetic transition. Ask judges to commit both predictions, then reveal the ray. Show a real model mistake only after the benchmark runs and use a physical camera frame only once captured. Label synthetic, human, model and physical evidence separately.
