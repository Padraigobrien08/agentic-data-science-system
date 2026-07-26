# Contributing

Thanks for contributing.

This project is a production-leaning EDGAR analysis system, so contributions should prioritize:

- deterministic behavior
- inspectability
- backward-compatible migrations
- auditability of runs and artifacts

## Before you open a PR

1. Read [README.md](README.md)
2. Read [docs/local-stack.md](docs/local-stack.md)
3. Make sure your change preserves the trust model:
   - deterministic numerical path stays inspectable
   - traceability surfaces remain explicit
   - auth and ownership boundaries remain safe

## Local setup

### Full stack

```bash
cp .env.example .env
docker compose up --build
```

### Backend-only

```bash
export PYTHONPATH=.
pip install -r requirements.txt -r requirements-backend.txt -r requirements-dev.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend-only

```bash
cd frontend
npm install
npm run dev
```

## Dependencies

The loose `requirements.txt`, `requirements-backend.txt`, and `requirements-dev.txt` are the
human-edited source of truth. Fully-pinned lockfiles are generated from them and are what the
Docker image (`requirements.lock`) and CI (`requirements-dev.lock`) install, so builds are
reproducible and `pip-audit` runs against exact versions.

After changing any `requirements*.txt`, regenerate the locks (resolved inside the Python 3.12
deploy image) and commit them alongside your change:

```bash
./scripts/compile-requirements.sh
```

## Tests

Run the most relevant checks for your change.

### Backend

```bash
PYTHONPATH=. python3 -m pytest tests/ -q --tb=short
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

For targeted frontend work, run focused Vitest slices before the full build.

## Contribution guidelines

- Prefer incremental seams over large rewrites
- Do not hide reasoning-critical behavior inside vague helper layers
- Keep backend/service errors explicit and mappable at the API boundary
- Preserve existing artifact and run inspection paths unless there is a migration plan
- Avoid speculative AI behavior in the deterministic numerical path
- Keep new UI work grounded in the existing product direction: chat-first, evidence-backed, traceable

## Pull requests

Good PRs usually include:

- the user-facing goal
- the architectural seam being changed
- verification steps run locally
- any migration or compatibility notes

## Scope preferences

High-value contributions:

- product clarity
- run trust
- observability
- evaluation quality
- deterministic analysis correctness
- deployability and operability

Lower-value contributions:

- cosmetic churn without product impact
- broad refactors without a clear trust or maintainability win
- abstractions that hide important execution behavior
