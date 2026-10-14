# TalentLens

TalentLens is an AI-powered candidate sourcing and scoring tool for recruiters. A recruiter submits a job description — as pasted text or an uploaded document — and TalentLens automatically parses it, searches public platforms (GitHub and Stack Overflow) for matching profiles, scores each candidate against the JD using an LLM, and returns a ranked list ready to review or export.

---

## What It Does

### Job Description Parsing

When a recruiter submits a JD, the AI service reads it and extracts structured information automatically: required skills, technologies, experience level, qualifications, domain, and a plain-language summary. The recruiter sees this parsed summary before sourcing begins, giving them confidence that the search is aligned with what the hiring manager actually wants. No manual tagging or form-filling is required.

### Candidate Sourcing

Once the JD is parsed and the search is saved, the recruiter can trigger candidate sourcing. TalentLens constructs targeted search queries from the parsed JD and runs them against the GitHub and Stack Overflow APIs simultaneously. When sourcing completes, the results are ready in the search detail view.

Each sourcing run is identified by a unique run ID, so a recruiter can re-run sourcing for the same search (to get fresh results) without losing the history of previous runs.

### Candidate Scoring and Ranking

Every sourced candidate is scored by the OpenAI LLM. The score is computed deterministically:

- **Skill match** accounts for 60% of the score — how closely the candidate's publicly visible skills align with those required in the JD.
- **Experience match** accounts for 40% — how well the candidate's background fits the stated experience level.

The final score is a number from 0 to 100. Candidates are presented ranked from highest to lowest. Up to 20 top candidates are returned per sourcing run.

### Access Control and Search Sharing

TalentLens has two user roles:

- **Recruiter** — can create searches, trigger sourcing, manage candidates, approve or reject access requests, and export results.
- **Hiring Manager** — read-only access. They can browse the list of recruiters, request access to a specific search, and once approved, view and export the candidates from that search.

This sharing workflow gives hiring managers visibility into the candidate pipeline without giving them write access to the system.

### Export

Any user with access to a search can export the candidate list as a CSV file. The export includes candidate name, profile URL, source platform, skills, location, bio, match score, and score breakdown.

---

## Technical Architecture

```mermaid
flowchart TB
    Browser["Browser\nReact UI"]

    subgraph App["TalentLens service (FastAPI)"]
        Static["Static UI\n(built React app)"]
        Api["REST API /api\nauth, searches, sharing, export"]
        Sourcing["Sourcing workflow\nquery generation + scoring"]
        Parser["JD parser\nLLM provider"]
    end

    subgraph Data["Data stores"]
        PG[("PostgreSQL\nusers, searches,\ntasks, share requests")]
        Mongo[("MongoDB\ncandidate profiles")]
    end

    subgraph External["External APIs"]
        LLM["OpenAI / Gemini"]
        GH["GitHub API"]
        Google["Google sign-in"]
    end

    Browser -->|"GET / (same origin)"| Static
    Browser -->|"REST + JWT + session cookie"| Api
    Api --> Parser
    Api --> Sourcing
    Api <--> PG
    Api <--> Mongo
    Sourcing --> Mongo
    Parser --> LLM
    Sourcing --> LLM
    Sourcing --> GH
    Api --> Google
```

TalentLens runs as **one service**. The FastAPI application in `talentlens-ai/` exposes the REST API, runs the LLM and sourcing work in-process, and serves the built React UI from the same origin. There is no separate frontend host and no CORS.

| Directory | What it is |
|---|---|
| `talentlens-ai/` | The service: FastAPI app (Python 3.12). Serves the API under `/api` and the UI at `/`. |
| `talentlens-client/` | The UI source: React 19 + TypeScript + Vite + Tailwind CSS. `npm run build` writes static files into `talentlens-ai/static/`. |

### Data stores

| Store | Holds | Access |
|---|---|---|
| PostgreSQL | Structured data: `users`, `searches`, `search_shares`, `sourcing_tasks`, `share_requests` | SQLAlchemy 2 ORM (async, psycopg) |
| MongoDB | Sourced candidate profiles (`candidates`), which vary by platform | Beanie ODM |

Tables and indexes are created on startup. Deleting a search removes its tasks, shares and share requests in Postgres (foreign-key cascade) and its candidates in MongoDB.

### Request flow

- **JD parsing** runs inside the request that creates a search (`POST /api/searches/jd-text` or `/jd-file`). The LLM call is moved to a worker thread so the server stays responsive.
- **Sourcing** is asynchronous. `POST /api/searches/{id}/source` records a task, returns `202`, and runs the workflow as a background task in the same process: generate queries, fetch profiles, score, store the top 20. The UI polls `GET /api/searches/{id}/source-status`. A run that exceeds the timeout, or that was interrupted by a restart, is marked `FAILED`.
- **Re-sourcing** calls the same endpoint again. Every run keeps its own candidates (keyed by `runId`); `GET /api/searches/{id}/runs` lists them newest first. The candidate list and export take an optional `runId` and otherwise show the latest completed run.

### Authentication and session security

Every route except sign-in and registration requires authentication, including the internal `/ai/*` routes that call the LLM (recruiters only).

A bearer token alone is not enough to call the API. Each session is bound to the browser it was issued to:

1. On sign-in the server generates a random **session fingerprint** and sends it only as an `HttpOnly`, `SameSite=Strict` cookie. Page scripts cannot read it.
2. The access and refresh tokens (JWT, HS256) carry `fgp`: an HMAC of that fingerprint, keyed with a **per-user salt** derived from the user's id and a secret stored on their row.
3. A request is authorised only when the token is valid **and** the cookie hashes to the token's `fgp` under that user's salt.

So a token copied out of `localStorage` is rejected without the cookie, and the cookie is useless without the token (which also rules out CSRF). Signing out rotates the user's salt, which revokes every token they hold on any device.

Also in place: bcrypt password hashing, rate limiting on the sign-in endpoints (5 attempts per minute per address), a Content-Security-Policy on the UI shell, and `/docs` disabled outside `APP_ENV=dev`.

Google sign-in uses the authorization-code flow with PKCE. The UI redirects to Google and the server exchanges the code and verifies the ID token.

---

## Running Locally

### Prerequisites

- **Docker** for PostgreSQL and MongoDB (or your own instances of both)
- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) (or `pip`)
- **Node.js 20.19+** and **npm**
- An **OpenAI** or **Gemini** API key, and a **GitHub** personal access token for sourcing

### Step 1: Start the databases

From the repo root:

```bash
docker compose up -d
```

This starts PostgreSQL on `5432` (`talentlens` / `talentlens`, database `talentlens`) and MongoDB on `27017` (`root` / `root`).

### Step 2: Configure the service

```bash
cd talentlens-ai
cp .env.example .env
```

Fill in `.env`. The database defaults already match `docker-compose.yml`; replace them with your own links if you host the databases elsewhere.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL link, e.g. `postgresql://user:pass@host:5432/db` (`?sslmode=require` is supported) |
| `MONGODB_URI`, `MONGODB_DATABASE` | MongoDB link and database name |
| `JWT_SECRET` | Token signing secret, at least 32 characters |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Google sign-in (optional) |
| `LLM_PROVIDER`, `OPENAI_API_KEY` / `GEMINI_API_KEY`, `GITHUB_TOKEN` | LLM and sourcing credentials |

### Step 3: Build the UI

```bash
cd talentlens-client
npm install
npm run build        # writes to ../talentlens-ai/static
```

For Google sign-in, set `VITE_GOOGLE_CLIENT_ID` in `talentlens-client/.env.local` before building.

### Step 4: Run the service

```bash
cd talentlens-ai
uv sync
uv run uvicorn app.main:app --port 9000
```

Open **http://localhost:9000**. The same server answers the UI, the API (`/api`), and the interactive API docs (`/docs`, dev only).

### Google sign-in redirect URI

Because the service now serves the UI, the OAuth redirect lands on the service's own origin. In Google Cloud Console, under the OAuth client's **Authorized redirect URIs**, add:

- `http://localhost:9000/oauth/google/callback` for local use
- `https://<your-domain>/oauth/google/callback` for each deployed environment

and add the matching origins under **Authorized JavaScript origins**. `GOOGLE_REDIRECT_URI` must equal the registered value exactly.

### Working on the UI

For hot reload, run the Vite dev server next to the service. It proxies `/api` to `http://localhost:9000`:

```bash
cd talentlens-client
npm run dev          # http://localhost:5173
```

Google sign-in from the dev server needs `http://localhost:5173/oauth/google/callback` registered as well, with `GOOGLE_REDIRECT_URI` pointing at it.

---

## Deployment

The root `Dockerfile` builds the UI and packages it with the service into one image:

```bash
docker build --build-arg VITE_GOOGLE_CLIENT_ID=<client id> -t talentlens .
docker run -p 9000:9000 --env-file talentlens-ai/.env -e APP_ENV=prod talentlens
```

With `APP_ENV=prod` the session cookie is `Secure` (HTTPS only) and `/docs` is off. Run it as a long-lived process: sourcing runs as an in-process background task and login rate limits are kept in memory, so serverless platforms that freeze the process between requests are not a fit.

---

## Migrating Data From the Old Backend

Data created by the earlier Spring Boot backend lives only in MongoDB (`users`, `searches`, `sourcing_tasks`, `share_requests`, `candidates`). `scripts/migrate_legacy_mongo.py` moves the first four into PostgreSQL and re-keys the candidates to the new search ids.

```bash
cd talentlens-ai
uv run python -m scripts.migrate_legacy_mongo            # dry run: reports what would happen, writes nothing
uv run python -m scripts.migrate_legacy_mongo --apply    # performs the migration
```

It writes to the stores configured in `.env` (`DATABASE_URL`, `MONGODB_URI`). By default it reads the legacy collections from that same MongoDB database and re-keys the candidates in place. If the old data is somewhere else, set `LEGACY_MONGODB_URI` and `LEGACY_MONGODB_DATABASE`, and the candidates are copied instead.

The script can be re-run safely and never deletes anything. Passwords keep working; everyone signs in again. Records it cannot place (for example a search whose owner no longer exists) are listed in the report and left where they are.

---

## Running Tests

```bash
cd talentlens-ai
uv run pytest

cd talentlens-client
npm run lint
npm run build        # includes the TypeScript check
```
