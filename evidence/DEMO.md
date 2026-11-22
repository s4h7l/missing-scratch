# Demo and model protocol

The opening question is whether a vision model notices a coverage change that could leave a target uninspected. The simulator is an ideal layout illustration. The fixed paired benchmark, independent answers and recorded evidence are the submission.

## 90-second finalist flow

1. Introduce the inspection decision with a marked target and a camera. Ask whether a moved obstruction changes what the camera can see.
2. Record findings for both paired scenes in Inspection. Reveal the ideal reflection and compare both findings.
3. Show the matching physical camera frames when available and state the measured match count. Keep the Evidence page open for the blind review, geometry and capture provenance.
4. On Benchmark, show per-task accuracy, strict pair accuracy and the gap to question-only performance. Spotlight one measured failure case with its count.

## Direct model comparison

Use image-capable IDs for Gemini, Claude and Qwen-VL. Use the existing Gemini route or one common OpenRouter route for the direct comparison. An image-capable OpenAI model is an optional fourth direct entry. Reuse the frozen image bytes, question wording, option order and scoring across providers. Match each vision run with a question-only run. Record the exact endpoint, model and date. No model has been run for this redesign.

Codex CLI supports image attachments. Evaluate it separately as an agent workflow, recording the selected model, CLI version and tool policy. Use an isolated workspace containing the input image only, with no repository, answer manifest, saved conversations, or answer keys. If any tools are allowed, record their use and keep the result out of the direct-model ranking.

## Framer handoff

The working app is in the repository. Framer can import the presentation layout or host a landing site that links to the published application. The benchmark routes, dataset and simulator currently run in the standalone app. To edit an actual Framer project, supply the project link or connect its Framer MCP project. For GitHub publishing use the requested ashrathdevx account and a specified repository.
