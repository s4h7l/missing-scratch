# Live inspection

Run `docker compose up --build`, then visit http://127.0.0.1:8000/#live. Generate any of the three task kinds, choose an option, then reveal the verified diagram. In paired mode both predictions must be locked first. Same-origin HTTP-only cookies bind the predictions to the browser. The results panel reads V3 benchmark and validation counts from the API. Frozen V4 inspection, simulator and reports retain their own data and scoring semantics.

The combined service exposes /health and /openapi.json and serves only the built public assets at /. SQLite persists in the inspection-data volume. Operator routes require MS_OPERATOR_TOKEN in the service environment. Live model requests require server-side provider configuration and a positive request budget. The ordinary prediction flow is offline.

For local development use Python 3.12, install the root requirements.txt and requirements-backend.txt in an environment with compatible dependencies, run python -m scratch.build, overlay datasets/v4/ into dist/ as in the Dockerfile, and run python -m uvicorn integrated_app:app --port 8000.
