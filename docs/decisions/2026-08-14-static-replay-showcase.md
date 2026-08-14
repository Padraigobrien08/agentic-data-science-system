# Direction: static replay showcase, then Oracle free tier

Date: 2026-08-14 · Status: **accepted**

Amends the hosting half of
[`2026-08-11-showcase-direction.md`](./2026-08-11-showcase-direction.md) (D6/D7). The tier
model, spend guard, recordings, and demo narrative from that plan are unchanged.

---

## 1. What changed

D6 chose a VPS at ~$6–12/month. The budget conversation resurfaced the real constraint: a
**recurring** bill on a personal project is the thing being avoided, not this month's $6. The
free tiers that could remove it (Render, Railway's credit) fail this workload on the merits —
they sleep idle services (a reviewer's first click must not cold-start for 45 seconds), they
exclude always-on workers, and their free Postgres expires, which for a demo *made of database
rows* means the demo itself expires.

Two decisions:

### D9 — Short term, the replay tier ships as a static export on Vercel's free tier

The replay tier already carries most of the demo weight (D3), and a published demo is
read-only persisted state served by four `GET` routes. So: export the two published
investigations — the `/v1/demos` list, each slug's full detail, and the ~128 KB of artifact
blobs behind them — into the frontend as committed files, and serve the whole showcase from
Vercel's free tier with **no backend at all**. Cost: $0/month, forever. The CV link cannot
rot when a box dies or a card expires.

What this deliberately gives up until D10: live guest runs, the invite-code adaptive tier,
and a live `/v1` + MCP endpoint. The README must say so plainly — the static showcase renders
*recorded* runs, and claiming more would be exactly what a reviewer checks for.

### D10 — Medium term, the full stack targets Oracle Cloud Always Free

A real VM (4 ARM cores / 24 GB) at $0/month, so every landed S2 asset — prod compose,
Caddyfile, deploy workflow, runbook — applies unchanged. Not attempted first because signup
and ARM capacity are notoriously flaky; it is worth one honest attempt, not a week. The
static showcase is not throwaway en route: it remains the permanent floor under the live
deployment, the thing the CV link degrades to instead of a 404.

## 2. Shape of the static tier

The rule that makes this safe: **the static path serves the same bytes the API would.**

- **Export** — `scripts/export_demo_static.py` reads the local database through the same
  service and schema builders the public routes use (`list_published`/`build_summary`,
  `get_published`/`build_detail`), so the JSON is the API contract, not a parallel
  serialization. Artifact blobs are copied from artifact storage. Output is committed:
  list + per-slug detail JSON under `frontend/src/lib/demo-static/`, blobs under
  `frontend/public/demo-data/`.
- **One data source seam** — `frontend/src/lib/api/demos.ts` serves demos from the static
  export when `API_URL` is unset, and proxies `/v1/demos*` when it is set. Pages never know
  which mode they are in; when D10 lands, the same pages go live by setting one env var.
- **Public pages** — `/demos` and `/demos/[slug]`, rendering with the existing
  `InvestigationDetailView`. The component gains optional seams (artifact href, parent-run
  link) rather than a fork; an authenticated user's investigation page and the public demo
  page stay the same component, which is the D3 claim ("rendered by the same UI as a live
  run") made true in code.
- **The shell already degrades.** `getCurrentUser()` returns `null` on any API failure, so
  the layout and landing page work with no backend configured. Auth entry points get an
  honest "the live tiers are not deployed in this showcase" notice instead of a 500.

## 3. What this is betting on

Same bet as the parent plan — demonstrated engineering over claimed engineering — plus one
addendum: **a portfolio link is a liability with a decay rate.** A $0 static tier with no
moving parts is the only version of this demo guaranteed to still work when a reviewer
clicks it eight months from now.
