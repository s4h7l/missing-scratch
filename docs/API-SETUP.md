# Model API setup

Create a project key in [Google AI Studio](https://aistudio.google.com/app/apikey), [GroqCloud](https://console.groq.com/keys), or the [Claude Console](https://platform.claude.com/settings/keys). Choose an organization or workspace you control. Enter keys only in a trusted local shell or secret manager. The benchmark site does not accept keys.

| Service | Runner provider | Environment variable |
|---|---|---|
| Gemini | gemini | GEMINI_API_KEY |
| GroqCloud | groq | GROQ_API_KEY |
| Claude Platform | anthropic | ANTHROPIC_API_KEY |
| OpenAI API (for direct GPT benchmark) | openai | OPENAI_API_KEY |
| OpenRouter | openrouter | OPENROUTER_API_KEY |

Codex CLI can use your ChatGPT login. Check with `codex login status`. The agent CLI is a separate evaluation from direct OpenAI model requests. A ChatGPT login does not populate the Missing Scratch runner's OpenAI API key. If you want direct GPT model results, use an [OpenAI project key](https://platform.openai.com/api-keys).

## Set keys without echoing them

In the same zsh terminal you use to run the benchmark:

```zsh
read -rs 'GEMINI_API_KEY?Gemini key: '; echo; export GEMINI_API_KEY
read -rs 'GROQ_API_KEY?Groq key: '; echo; export GROQ_API_KEY
read -rs 'ANTHROPIC_API_KEY?Claude key: '; echo; export ANTHROPIC_API_KEY
# Optional direct GPT API comparison:
read -rs 'OPENAI_API_KEY?OpenAI key: '; echo; export OPENAI_API_KEY
```

Pick an image-capable model ID available in each account. The Groq [vision documentation](https://console.groq.com/docs/vision) lists supported models and image limits. Groq runs a selected model, so cite the exact model ID and provider in reported results.

For a capped Groq smoke run, replace the model placeholder with a vision model ID supported by your project:

```sh
.venv/bin/python -m scratch.evaluate --dataset runs/frozen-200-v4/cases.json \
  --provider groq --model YOUR_GROQ_VISION_MODEL --mode vision \
  --max-requests 2 --record runs/groq-smoke.jsonl
```

A smoke run should never be published as a benchmark result. For publication, run the full frozen dataset in both vision and question-only modes and use distinct log paths. API calls can incur usage charges.
