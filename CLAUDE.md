# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

TalentLens is an AI-powered recruiter tool that sources and scores candidates from public developer platforms based on job descriptions.

It runs as **one service**. There is no separate backend, frontend host, or message broker.

```
talentlens-ai/        # The service: Python 3.12 + FastAPI. REST API, LLM work, sourcing, and it serves the built UI.
talentlens-client/    # UI source: React 19 + TypeScript + Vite + Tailwind CSS. Builds into talentlens-ai/static/.
```

The Spring Boot backend that used to sit between the two was removed; its responsibilities (auth, searches, sharing, export, sourcing orchestration) now live in `talentlens-ai/`.

**Data stores:**
- **PostgreSQL** holds structured data (`users`, `searches`, `search_shares`, `sourcing_tasks`, `share_requests`) through the SQLAlchemy 2 async ORM (`app/db/models.py`).
- **MongoDB** holds sourced candidate profiles (`candidates`) through the Beanie ODM (`app/db/documents.py`).

Tables and indexes are created at startup (`create_all` / Beanie). There is no migration tool yet, so a change to an existing column needs a manual migration.

### Key Data Flow

**JD parsing (in the request):**
UI → `POST /api/searches/jd-text|jd-file` → LLM provider (in a worker thread) → Postgres → response

**Candidate sourcing (in-process background task):**
UI → `POST /api/searches/{id}/source` → task row + `202` → FastAPI `BackgroundTasks` job (runs after the response, inside the same request): LLM query generation → platform adapters in parallel → scoring → top 20 into MongoDB → task/search updated in Postgres. The UI polls `GET /api/searches/{id}/source-status`.

**Candidate sources** (`app/services/sources/`): one adapter per platform (GitHub, Stack Overflow, Hacker News "Who wants to be hired?", dev.to, Hugging Face, npm, crates.io, GitLab, OpenAlex). `registry.py` lists them with the settings each needs (a platform without them is offered as unavailable) and when to suggest each for a JD (`auto` mode). Adapters get the parsed JD as well as the LLM's queries and derive their own search terms, so sourcing still works when the LLM falls back. Adapters are shared across runs: keep per-run state in locals. To add a platform: an adapter, a `SourcePlatform` value, a registry entry, a line in `PLATFORM_QUERY_RULES` (`app/prompts/templates.py`), and `PLATFORM_META` in the UI (`src/utils/platforms.ts`). `scripts/sourcing_eval.py` measures sourcing quality against fixed JDs (no database needed).

### Deployment

Production runs on **Vercel** as one Python function (`talentlens-ai/vercel.json`, `[tool.vercel]` in `talentlens-ai/pyproject.toml`); the root `Dockerfile` is the alternative. Constraints that follow from Vercel:
- Keep post-response work on `BackgroundTasks`, never a detached `asyncio.create_task`: Vercel ends the invocation when the ASGI call returns and may freeze the instance, so detached work can stall halfway. It must also finish within the function's `maxDuration` (300 s).
- Do not rely on process startup for cleanup. Stale sourcing runs are failed at startup and again when their status is polled.
- Request bodies are capped at 4.5 MB (JD uploads are limited to 4 MB to fit). Login rate limits are in memory, so they are per instance.
- The UI is served by the function, not the CDN (`[tool.vercel.fastapi.static] cdn = false`), so the UI shell keeps the app's security headers.

### Roles
- `RECRUITER`: full access (create/delete searches, trigger sourcing, export candidates, resolve share requests)
- `HIRING_MANAGER`: read-only access to searches a recruiter has shared with them, and can request access

### Auth model (read before touching `app/security/`)

A bearer token alone never authorises a request. At sign-in the server sets a random session fingerprint as an `HttpOnly` cookie, and the JWT carries `fgp`, an HMAC of it keyed by a per-user salt (`users.token_salt`, mixed with the user id and `JWT_SECRET`). `load_bound_user` in `app/security/auth.py` checks both. Rotating `token_salt` (done on logout) revokes all of a user's tokens.

- New routes need `Depends(get_current_user)` or `require_recruiter` / `require_hiring_manager`. Anything that spends LLM quota must be recruiter-only.
- Never return `token_salt`, the fingerprint, or `password_hash` in a response.
- Access rules live in the services: use `get_viewable_search` (owner or shared, otherwise 404) and `assert_ownership` (403).

## Commands

### Service (`talentlens-ai/`)
```bash
uv sync                                   # installs into .venv (pip install -r requirements.txt also works)
uv run uvicorn app.main:app --port 9000 --reload   # http://localhost:9000 (UI, /api, /docs)
uv run pytest
```
Dependencies are pinned in both `pyproject.toml` and `requirements.txt`; keep them in step (the Docker image installs from `requirements.txt`).

### UI (`talentlens-client/`)
```bash
npm install
npm run build        # type-checks, then writes static files to ../talentlens-ai/static
npm run dev          # Vite dev server on http://localhost:5173, proxies /api to :9000
npm run lint
```
The service serves whatever is in `talentlens-ai/static/` (git-ignored). After changing UI code, rebuild to see it on `:9000`.

### Local databases and image
```bash
docker compose up -d     # PostgreSQL :5432 + MongoDB :27017
docker compose down
docker build --build-arg VITE_GOOGLE_CLIENT_ID=<id> -t talentlens .   # UI + service in one image
```

## Environment Variables

All service settings are read from `talentlens-ai/.env` (see `.env.example` and `app/config.py`).

| Key | Notes |
|-----|-------|
| `DATABASE_URL` | PostgreSQL link; `postgres://` and `postgresql://` are both accepted |
| `MONGODB_URI`, `MONGODB_DATABASE` | MongoDB link and database |
| `JWT_SECRET` | Required, at least 32 characters |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Redirect URI = the origin the app is opened on + `/oauth/google/callback`. Comma-separate several (e.g. `:9000` and the Vite dev server's `:5173`); each must be registered in Google Cloud Console. The UI sends the one it used and the server accepts only listed ones, because Google rejects a code exchange whose URI differs from the sign-in's |
| `LLM_PROVIDER`, `OPENAI_API_KEY`, `GEMINI_API_KEY` | LLM credentials |
| `GITHUB_TOKEN`, `GITLAB_TOKEN`, `SOURCING_CONTACT` | Required by GitHub, GitLab and crates.io sourcing respectively |
| `STACKEXCHANGE_KEY`, `HF_TOKEN`, `OPENALEX_API_KEY` | Optional; raise Stack Overflow / Hugging Face / OpenAlex limits. On Vercel's shared IPs the Stack Exchange key is effectively required |
| `APP_ENV` | `dev` enables `/docs` and non-`Secure` cookies; anything else is treated as production. Unset, it is `prod` on Vercel production/preview deployments (`VERCEL_ENV`) and `dev` elsewhere |

UI build-time: `VITE_GOOGLE_CLIENT_ID` (and `VITE_API_BASE_URL` as the dev-server proxy target) in `talentlens-client/.env.local`.

## LLM Usage

- Provider is chosen at runtime by `LLM_PROVIDER` (`openai` or `gemini`), behind `app/providers/base.py`.
- **JD parsing & query generation:** temperature 0, JSON output validated with Pydantic; falls back to a heuristic parser if the provider fails.
- **Candidate scoring** is deterministic (`app/services/scoring_service.py`): 60% skill match, 40% experience match. Skills are compared in canonical form (`app/services/skill_vocabulary.py`: `golang` = `go`, `postgres` = `postgresql`) against the JD's technologies (topped up with its skills when it names fewer than 3), at most 10 terms. Unknown experience scores a neutral 50. Ties go to candidates who are open to work, and each platform that found anyone keeps up to 3 of the top 20.
- Provider calls are blocking; call them through `asyncio.to_thread` from async code.

## API Surface

All UI-facing routes are under `/api/`. Only register, login, refresh, logout and the Google endpoints are public.

- `POST /api/auth/register|login|refresh|logout`, `GET /api/auth/me`, `POST /api/auth/google/callback|complete-signup`
- `POST /api/searches/jd-text|jd-file`, `GET /api/searches`, `GET|DELETE /api/searches/{id}`
- `POST /api/searches/{id}/source` with `{ platforms }` or `{ auto: true }` (also re-sources: each call is a new run), `GET /api/searches/{id}/source-status`, `GET /api/searches/{id}/runs`
- `GET /api/sourcing/platforms` (recruiter-only): each platform and whether this server is configured for it
- `GET /api/searches/{id}/candidates`, `GET /api/searches/{id}/candidates/export`, `DELETE /api/searches/{id}/candidates/{candidateId}`. Candidates and export take `runId`; without it they use the latest completed run.
- `GET /api/share-requests/recruiters`, `GET /api/share-requests/recruiters/{id}/searches`, `POST /api/share-requests`, `GET /api/share-requests/incoming|outgoing`, `POST /api/share-requests/{id}/approve|reject`
- Recruiter-only LLM utilities: `POST /ai/parse-jd`, `/ai/parse-jd-file`, `/ai/generate-queries`, `/ai/source-candidates`

Errors use one shape: `{ "error": CODE, "message": ..., "timestamp": ..., "path": ... }`. JSON fields are camelCase.

Any other `GET` path returns the UI shell so client-side routes work on reload (`app/web.py`). Register API routes before `mount_ui` in `app/main.py`.

## Source Layout

```
talentlens-ai/app/
  main.py          # app wiring: lifespan, middleware, routers, UI mount
  config.py        # settings (pydantic-settings)
  errors.py        # AppError hierarchy + exception handlers
  web.py           # static UI + SPA fallback
  api/             # routers: auth, searches, candidates, share_requests, jd_parser, sourcing, platforms
  security/        # tokens (JWT + session binding), auth dependencies, passwords, rate_limit
  services/        # business logic: auth, google_oidc, search, sourcing, candidate, export, share_request,
                   #   plus jd_parser, sourcing_workflow, scoring, skill_vocabulary
  services/sources/  # one adapter per sourcing platform + registry.py (availability, suggestions)
  db/              # postgres.py (engine/session), models.py (ORM), mongo.py, documents.py (Beanie)
  models/          # Pydantic request/response schemas
  providers/       # LLM providers (openai, gemini) behind a common interface
  prompts/         # prompt templates + JSON response parsing
talentlens-ai/tests/   # pytest unit tests (no database needed)
talentlens-ai/scripts/ # one-off tools, e.g. migrate_legacy_mongo.py (old Spring Boot MongoDB data -> current stores)

talentlens-client/src/
  api/             # Axios instance + API functions (maps API fields to UI types)
  components/      # Reusable UI
  pages/           # Login, Register, OAuthCallback, Dashboard, NewSearch, SearchDetail, ShareRequests
  hooks/           # TanStack Query hooks
  stores/          # Zustand stores (auth, ui)
  types/           # TypeScript interfaces
```

## Specification Files

`specs/` and `requirements/` are git-ignored and local only. They describe the original three-service design (Spring Boot + Kafka), which is no longer how the system is built; treat them as product background, not as the architecture.
