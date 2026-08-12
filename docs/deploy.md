# Deploying the hosted demo

Frontend on Vercel, backend on one small VPS. Target cost is under $25/month all-in
(see [`decisions/2026-08-11-showcase-direction.md`](./decisions/2026-08-11-showcase-direction.md), D6/D7).

```
   browser ──HTTPS──▶ Vercel (Next.js)
                          │  server-side fetch, never from the browser
                          ▼
                   Caddy :443  ──▶  api:8000
                                     ├─ worker
                                     ├─ retention
                                     └─ db (Postgres, in-compose)
```

**The browser never talks to FastAPI.** Next.js keeps proxying server-side, so the JWT stays in
an HttpOnly cookie on the Vercel origin and `cors_allow_origins` stays empty. The cost is one
cross-internet hop per render — put the VPS in the same region as your Vercel functions.

---

## 1. Server

Any 2 GB / 1 vCPU box (Hetzner CX22, DigitalOcean basic) is enough: the heavy build is on
Vercel, so this host only builds a slim Python image.

```bash
# as root, on a fresh Debian/Ubuntu box
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy          # after installing Docker Engine + compose plugin
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw enable
```

Point an `A` record at the box **before** the first `up` — Caddy requests a certificate for
`EDGAR_API_DOMAIN` on boot and the ACME challenge fails if the name does not resolve yet.

```bash
sudo -u deploy -i
git clone <repo> /srv/edgar && cd /srv/edgar
cp .env.production.example .env && chmod 600 .env
# fill in every blank; generate secrets with: openssl rand -base64 36
```

`docker-compose.prod.yml` marks every secret `:?`, so a half-filled `.env` fails at
`config` time rather than starting with a development posture on the public internet. Verify
before starting:

```bash
docker compose -f docker-compose.prod.yml config --quiet && echo ok
```

Then:

```bash
docker compose -f docker-compose.prod.yml up -d --build
curl -fsS https://$EDGAR_API_DOMAIN/v1/health | jq
```

`migrate` runs `alembic upgrade head` as its own service and gates `api`/`worker` via
`service_completed_successfully`, so schema changes apply in order and a failed migration stops
the app from starting rather than half-starting it.

## 2. Frontend (Vercel)

Import the repo, set **Root Directory** to `frontend`, and add one environment variable:

| Variable | Value |
|---|---|
| `API_URL` | `https://api.your-domain.com` |

That is the whole configuration. `API_URL` is read server-side only
([`config.ts`](../frontend/src/lib/api/config.ts)) and throws at build time in production if
missing, so a misconfigured deploy fails loudly instead of rendering an empty app.

Do **not** set `NEXT_PUBLIC_API_URL` or anything similar — a `NEXT_PUBLIC_` variable is inlined
into the browser bundle, which is exactly the direct-to-FastAPI path this architecture avoids.

## 3. First admin

Registration is open but lands everyone in the standard (deterministic) tier. Bootstrap
yourself an admin, which is exempt from the spend ceilings:

```bash
curl -X POST https://$EDGAR_API_DOMAIN/v1/auth/bootstrap \
  -H "X-EDGAR-Bootstrap-Token: $EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"<at least 10 chars>"}'
```

The endpoint refuses once an admin exists, so it is safe to leave the token configured.

## 4. Seed the replay tier

The published demos are what an unauthenticated visitor sees, and they do not travel with the
repo — they are database rows plus artifact blobs. **Record them on the server**, not locally:
the blobs must land on the server's `artifacts` volume, and a row pointing at a `local:` key
that only exists on your laptop is a broken demo.

```bash
docker compose -f docker-compose.prod.yml exec api \
  python3 scripts/record_demo.py edgar --tickers AAPL,MSFT,NVDA \
    --goal "Has margin quality deteriorated at these companies over recent periods, or is revenue growth the explanation?" \
    --publish edgar-margin-vs-growth

docker compose -f docker-compose.prod.yml exec api \
  python3 scripts/build_demo_dataset.py

docker compose -f docker-compose.prod.yml exec api \
  python3 scripts/record_demo.py csv \
    --goal "Delivery times in the north region have worsened. Is service quality actually degrading, or is rising order volume the explanation?" \
    --publish csv-delivery-delays
```

Roughly $0.02 of model spend, and it doubles as an end-to-end smoke test of the deployed stack
— SEC fetch, pipeline, loop, artifact ingestion and publication all in one command. Confirm:

```bash
curl -fsS https://$EDGAR_API_DOMAIN/v1/demos | jq '.[].id'
docker compose -f docker-compose.prod.yml exec api python3 -m backend.maintenance.publish_demo list
```

A recording is not published until `--publish` succeeds, so you can inspect one first and
publish it separately with `publish_demo publish <investigation-id> --slug <slug>`. Unpublishing
revokes the investigation *and* its artifacts in the same step.

## 5. Redeploys

`.github/workflows/deploy.yml`, triggered manually (`workflow_dispatch`). It runs the suite,
ruff and the API-contract check, then over SSH: `git reset --hard origin/main`,
`compose up -d --build`, and finally asserts `/v1/health` returns 200 **and** `/v1/demos` is
non-empty — because a deploy that leaves the replay tier empty is a broken demo even when
health is green.

Repository secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_PATH`.

The server's `.env` is deliberately **not** managed by the workflow. It holds the OpenAI key
and the JWT secret; keeping it on the host means a compromised CI token cannot read them.

---

## What is deliberately not here

- **Backups / restore (`O2`).** Closed as won't-do: there is no user data worth recovering and a
  reviewer cannot see a restore procedure. If this ever takes real users, it reopens first.
- **The observability stack.** `docker-compose.observability.yml` (Prometheus, Grafana, Jaeger)
  stays local-only — it costs RAM this box does not have. The dashboards ship as screenshots.
  Caddy also 404s `/metrics` and `/v1/worker/health`, so ops surfaces are not merely
  token-gated but unreachable from the internet.
- **Multi-replica anything.** Auth rate limiting is in-process
  ([`rate_limit.py`](../backend/api/rate_limit.py)); a second API replica would enforce it
  independently. Single replica is the supported topology here.

## Cost control

The spend guard is the thing standing between an open registration form and a surprise bill.
Two independent controls, both configured in `.env`:

- **Run-count ceilings** always bind. These are the real backstop.
- **USD ceilings** bind *only* when `EDGAR_BACKEND_LLM_MODEL_PRICES` is set — an unpriced model
  estimates every call at $0.00 and the dollar limits silently become no-ops. The compose file
  marks that variable `:?` for exactly this reason, and the API logs
  `spend_guard_usd_ceilings_inert` at startup if it is ever bypassed.

When the global monthly ceiling is reached, live runs stop and the replay tier keeps serving —
the demo degrades visibly rather than draining a card. Check the posture any time with:

```bash
docker compose -f docker-compose.prod.yml logs api | grep spend_guard_posture
```
