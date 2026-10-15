# EluSim_V1 production deployment

Chosen architecture: one Docker web service serves both the built React app and Python `/api`. This gives one HTTPS origin and avoids cross-origin credentials. Scientific work is server-side RDKit/SciPy, not a static demo. Projects stay in browser storage / explicit local export; there is no server endpoint to read another visitor's project.

## Provider comparison and selected configuration

Render Docker web service is the initial target, Singapore, **free** plan. [Render web services](https://render.com/docs/web-services) supports public HTTPS and Docker from Git. [Free limitations](https://render.com/docs/free): spin down after 15 minutes idle, cold-start delay, resource/usage limits, ephemeral filesystem. Free does not mean an always-warm guarantee. The app runs on the provider, independent of the developer computer. If free CPU/RAM fails acceptance, changing to a paid plan requires the user's approval. [Pricing](https://render.com/pricing), checked 2026-10-13, lists Starter 512 MB at $7/month; bandwidth/add-ons may change the total. No paid service is silently provisioned.

Railway is a Docker alternative, with subscription + usage billing ([plans](https://docs.railway.com/pricing/plans)). Fly.io offers configurable machines and usage billing ([pricing](https://fly.io/docs/about/pricing/)), but adds machine/network configuration. Cloudflare/Sites Workers can front a separate service but do not replace this native Python/RDKit container. No Cloudflare static-only deployment is counted as V1.

## Files and release steps

- `Dockerfile`: Node build stage, locked Python dependencies, non-root runtime, health check and corresponding-source package.
- `compose.yaml`: reproducible local container, memory/CPU ceiling, read-only filesystem / temporary area. Local compose is not a public URL.
- `render.yaml`: provider blueprint; `feature/elusim-v1`, free plan, `/api/health`.
- `.env.example`: nonsecret runtime options; no provider tokens in source/frontend.
- GitHub Actions: Python tests, TypeScript/Vite build, Linux Docker build/health, optional protected production deploy hook. Prefer provider auto-deploy only after checks pass. If the hook is used, put it in GitHub Environment `production`, secret `RENDER_DEPLOY_HOOK`, never in a tracked file or log.

Create/confirm the GitHub feature branch, run CI, then deploy the exact source commit on Render. The workspace confirmed by the user is `My Workspace` (`tea-db6qffon74is738k4q30`). Repository: https://github.com/T22016AEMC/EluSim. Actual service ID, URL, deployment and public checks must be recorded from provider results in the acceptance report; no guessed URL is allowed.

`SOURCE_REVISION` can carry the Git SHA; on Render, the health endpoint also uses the provider's `RENDER_GIT_COMMIT`. `/api/source` serves source, dependency locks, licenses, third-party reference/provenance, scientific tests and build instructions from the deployed image. Model & Column Library links to that source offer. EluSim source is AGPL-3.0-or-later; binary dependency notices remain applicable, see the generated Python/JS license inventories and NOTICE.

## Runtime safety and persistence

One Uvicorn worker, at most two disposable science processes. Hard process deadline 30s, optimization/calibration internal deadline 20s, max 20 compounds, 40 nodes, 2,000 plot samples, 24 optimization candidates, request limit 1 MiB / file limit 900 kB, 30 POST requests/minute per direct client address. The limiter is in-process; a reverse proxy may aggregate visitors because proxy headers are not blindly trusted. At higher traffic, use a trusted ingress-aware distributed limiter, task queue and measured capacity before scaling workers.

No anonymous external URL fetch or PubChem dependency; RDKit local name aliases are intentionally limited. No API keys in browser. Input validation, same-origin CSP, no embedded frames, non-root container, bounded response size. A browser-aborted request may continue until its server deadline, but cannot overwrite newer client results.

No durable user project database is needed for anonymous V1. SQLite/Postgres storage must only be enabled after owner/auth isolation; provider ephemeral filesystem is not presented as durable project storage. `database/` documents this boundary.

## Public acceptance commands

After a provider returns a successful live URL, replace the placeholder below with that **observed** origin:

```sh
python scripts/public_smoke.py https://OBSERVED-LIVE-ORIGIN
cd frontend
ELUSIM_BASE_URL=https://OBSERVED-LIVE-ORIGIN pnpm test:e2e
```

Public smoke checks homepage, online RDKit, backend health, real simulation, optimization and source archive. Browser suite checks chart rendering, method edits, applying candidates, reload, unsupported modes and desktop/mobile layout. These run from a client outside the provider and reach public HTTPS, with no LAN dependency. Distinguish Pixel 7 browser emulation from physical-device/cellular testing. If the live service is absent or any public test fails, deployment acceptance remains incomplete.
