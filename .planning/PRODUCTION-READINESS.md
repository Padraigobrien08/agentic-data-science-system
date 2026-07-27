# Production Readiness Backlog

Tracking list of gaps between the current system and a production-ready posture.
The application itself is mature (200+ backend tests, e2e, Compose w/ healthchecks +
one-shot migrations, structured logging/tracing/metrics, real config sanity checks).
The gaps below are the *production envelope* around it.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done
Effort: S (<1h) · M (half day) · L (multi-day)

_Last updated: 2026-07-27 — C1 done (OpenAI key rotated; secrets-manager migration remains open). E1 landed (pinned lockfiles; pip-audit now blocking); E4 landed (coverage floor 80%, baseline ~84%); C2 landed (auth rate limiting); C3 landed (security headers + opt-in CORS); E2 complete (dependabot + pip-audit + npm audit + CodeQL + gitleaks + Trivy); E3 landed (ruff blocking, mypy report-only); O1 landed (retention windows + sidecar scheduler)._

---

## 🔴 Critical — before any real deployment

- [x] **C1. Rotate the exposed OpenAI API key** — S
  - [x] Rotated 2026-07-27: new key generated, swapped into `.env`, verified reachable (HTTP 200), old `sk-proj-…` key revoked. (The key was never committed/pushed — gitignored and absent from git history — but had been surfaced to the terminal/logs.)
  - [ ] **Follow-up (open): move secrets out of plaintext `.env` into a secrets manager** (Vault / AWS Secrets Manager / SSM); secrets are still env-only. — M

- [x] **C2. Rate limiting / brute-force protection on auth** — M
  - [x] `backend/api/rate_limit.py`: in-process sliding-window limiter (no new dependency), applied to `/auth/login`, `/auth/register`, `/auth/bootstrap` via a FastAPI dependency; keyed by client IP + path. Returns 429 + `Retry-After`.
  - [x] Configurable (`EDGAR_BACKEND_AUTH_RATE_LIMIT_*`, default 10/60s), disable-able; documented in `.env.example`; covered by `tests/test_auth_rate_limit.py`.
  - _Caveat: per-process state — multi-replica deployments need a shared store (Redis) or an ingress limiter. Ties into O3 (deploy target)._

- [x] **C3. CORS posture + security response headers on the API** — M
  - [x] `SecurityHeadersMiddleware` (`backend/api/security_headers.py`) on all responses: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cross-Origin-Opener-Policy`, CSP (`default-src 'none'`; docs paths exempt), and HSTS (HTTPS-only, 2y default, 0 disables).
  - [x] CORS is **opt-in, closed by default** (`EDGAR_BACKEND_CORS_ALLOW_ORIGINS`); comma-separated or JSON list, with a settings guard rejecting `*` + credentials. Matches the server-side-proxy architecture.
  - [x] Documented in `.env.example`; covered by `tests/test_security_headers.py`.

## 🟠 Supply chain & CI — highest leverage

- [x] **E1. Pin dependencies / add a Python lockfile** — M
  - [x] Loose `requirements*.txt` stay the source of truth; fully-pinned `requirements.lock` (runtime) + `requirements-dev.lock` (runtime+dev) generated via `scripts/compile-requirements.sh`, resolved inside `python:3.12-slim` so pins match the deploy target.
  - [x] Dockerfile installs `requirements.lock`; CI installs `requirements-dev.lock`. Validated: locks resolve clean, full suite passes against the dev lock, image builds + app imports.
  - [x] Unblocked the ratchet: `pip-audit` now audits `requirements.lock` and is **blocking** (verified 0 known vulns). npm audit / gitleaks / trivy still report-only pending first-findings triage.
  - [x] Workflow documented in `CONTRIBUTING.md`; `.coverage`/lock artifacts handled in `.gitignore`.

- [x] **E2. Vulnerability + secret scanning in CI** — S each
  - [x] `.github/dependabot.yml` (pip + npm + actions) — grouped weekly updates
  - [x] `pip-audit` job — `.github/workflows/security.yml` (report-only until E1)
  - [x] `npm audit` job — `.github/workflows/security.yml` (report-only, high+ severity)
  - [x] CodeQL (SAST) — `.github/workflows/codeql.yml`, python + javascript-typescript; alerts → Security tab
  - [x] Image + IaC scan (Trivy) — `security.yml`: `trivy config` (Dockerfile/compose misconfig) + `trivy image` (built backend image CVEs)
  - [x] Secret scan (gitleaks) — `security.yml` (report-only; scans event commits, full history on cron)
  - _Ratchet: pip-audit is now **blocking** (E1 pinned deps, 0 vulns). npm audit / gitleaks / trivy remain report-only until their first findings are triaged._

- [x] **E3. Backend lint + type-check in CI** — S
  - [x] `ruff` — `ruff.toml`, **blocking** in CI (`quality` job). Codebase made green: 146 auto-fixed + 4 real fixes (dead vars, forward-ref import). E501/line-length not enforced.
  - [x] `mypy` — `mypy.ini`, **report-only** in CI (52 findings). _Ratchet: tighten config + flip to blocking as findings are burned down._

- [x] **E4. Coverage gate + reporting** — S
  - [x] `pytest-cov` + `.coveragerc`; CI backend job measures coverage over backend/edgar_project/src/agentic, writes `coverage.xml` (artifact) and a job-summary table.
  - [x] **Blocking** floor `--cov-fail-under=80` (baseline ~84%). Coverage args live in CI only so local `pytest` stays fast. _Ratchet the floor up toward baseline over time._

- [ ] **E5. Release/CD pipeline** — L
  - No tagged image build/publish for backend or frontend, no SBOM, no CD path. Deployment is manual `docker build`.

## 🟡 Operational readiness

- [x] **O1. Enable retention windows** — S
  - Root cause was two-fold: defaults were `0` **and** nothing scheduled the retention CLI, so it never ran.
  - [x] Code defaults stay `0` (safe for dev/tests/CLI). Deployed stack enables sensible windows via `docker-compose.yml` (`x-backend-env`): run payloads 90d, model payloads 30d, artifact blobs 180d — all overridable, `0` disables.
  - [x] Added a `retention` sidecar service that runs `python -m backend.maintenance.retention --apply` on a loop (default 24h, `EDGAR_BACKEND_RETENTION_INTERVAL_SECONDS`). Safe no-op when all tiers are 0.
  - [x] Documented all four knobs in `.env.example`.
  - _Note: retention only runs in the compose/deployed stack. Non-compose deployments must schedule the CLI themselves (host cron / external scheduler)._

- [ ] **O2. Backup/restore + DR** — M
  - No documented Postgres backup or artifact-storage durability/restore. Define RPO/RTO and a tested restore.

- [ ] **O3. Deployment target beyond single-host Compose** — L
  - No K8s/Terraform/managed-hosting manifests. No autoscaling, rolling deploys, or zero-downtime migration strategy.

- [ ] **O4. Alerting / dashboards / SLOs / log shipping** — M
  - Logs, `/metrics`, and OTel traces are emitted but have no consumers. Add alert rules, dashboards, SLOs, log aggregation.

- [ ] **O5. Load / performance testing** — M
  - Worker lease/retry + queue untested under concurrency/throughput.

---

## Suggested sequencing

1. **Today:** C1 (rotate key), E2 (Dependabot + audit jobs), E3 (ruff/mypy) — quick wins.
2. **This week:** C2, C3, E1, E4, O1.
3. **Before launch:** O2, O4, E5, O3, O5.

## Easy wins to start with

`C1` · `E2` · `E3` · `E4` · `O1` — mostly S-effort, high risk-reduction.
Code changes route through GSD (`/gsd:quick` for these).
