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
    subgraph Client["Frontend (Vercel)"]
        UI["React 18 + TypeScript\nTailwind CSS + Vite"]
    end

    subgraph Backend["Spring Boot API (Render — Docker)"]
        Auth["JWT Auth"]
        Search["Search CRUD"]
        Sourcing["Sourcing Orchestrator"]
        Share["Share Request Manager"]
        Export["CSV Export"]
    end

    subgraph AI["Python AI Service (Vercel)"]
        Parser["JD Parser\nGPT-4o-mini"]
        QueryGen["Query Generator"]
        Scorer["Candidate Scoring\nOpenAI LLM"]
    end

    subgraph DB["MongoDB Atlas"]
        Users[(users)]
        Searches[(searches)]
        Candidates[(candidates)]
    end

    subgraph External["External APIs"]
        GH["GitHub API"]
        SO["Stack Overflow API"]
    end

    UI -->|"REST + JWT"| Backend
    Backend -->|"POST /ai/parse-jd\nsync REST"| Parser
    Backend -->|"POST /ai/source-candidates\nsync REST"| QueryGen
    QueryGen --> Scorer
    Scorer -->|"scored candidates"| Backend
    Backend <--> DB
    QueryGen --> GH
    QueryGen --> SO
```

### Frontend — React (Vercel)

The frontend is a single-page application built with React 18, TypeScript, Vite 5, and Tailwind CSS. It communicates with the backend exclusively via REST over HTTPS. Axios is used as the HTTP client, with JWT access tokens attached to every authenticated request via an Axios interceptor. Expired tokens are refreshed automatically using the stored refresh token before retrying the original request.

State management is split between TanStack Query (server state: searches, candidates, sourcing status) and Zustand (client state: auth, UI theme). Page-level components are lazy-loaded to keep the initial bundle small.

The app is deployed to Vercel. Vercel's rewrite rules proxy all `/api/*` requests to the Spring Boot backend on Render, and route all other paths to `index.html` to support client-side routing.

### Backend — Spring Boot (Render)

The backend is a Java 21 Spring Boot 3 application, containerised with Docker and deployed on Render. It is the central coordinator of the system and the single source of truth for all persisted data.

Responsibilities:
- **Authentication** — JWT-based auth with access tokens (15-minute TTL) and refresh tokens (7-day TTL). Passwords are hashed with BCrypt.
- **Search management** — CRUD for searches, with auto-generated titles derived from the JD domain and a timestamp.
- **AI service integration** — calls the Python AI service synchronously (via WebClient) for JD parsing when a search is created.
- **Sourcing orchestration** — calls the AI service synchronously to trigger candidate sourcing; receives scored candidates in the response and persists them to MongoDB.
- **Search sharing** — manages the full share request lifecycle: hiring manager requests access, recruiter approves or rejects, persisted history on both sides.
- **Export** — streams a CSV of candidate data directly from MongoDB, formatted and returned as a file download.

The backend exposes all API routes under `/api/`. Internal routes used only by the AI service are prefixed `/ai/` and are not accessible to the frontend.

### AI Service — FastAPI (Vercel)

The AI service is a Python 3.12+ FastAPI application. It handles all LLM interaction and external API calls.

Responsibilities:
- **JD parsing** — called synchronously by the backend on search creation. Uses GPT-4o-mini at temperature 0.0 with a Pydantic output parser to extract skills, technologies, experience level, qualifications, domain, and a summary from the raw JD text or uploaded file.
- **Query generation** — produces targeted search queries for GitHub and Stack Overflow from the parsed JD.
- **Candidate sourcing** — called synchronously by the backend. Calls the GitHub API (repositories, users) and the Stack Overflow API (users by tags) to find candidate profiles matching the generated queries.
- **Candidate scoring** — the OpenAI LLM scores each sourced candidate against the JD. The top 20 scored candidates are returned to the backend in the response.
- **Provider abstraction** — LLM provider (Gemini or OpenAI) is selected at runtime via environment configuration, not hardcoded.

### Infrastructure

| Component | Technology | Hosting |
|---|---|---|
| Database | MongoDB Atlas | MongoDB Atlas Free Tier |
| Frontend | React + Vite | Vercel |
| Backend | Spring Boot 3 | Render (Docker) |
| AI Service | FastAPI | Vercel |

---

## Running Locally

### Prerequisites

Make sure the following are installed before starting:

- **Docker and Docker Compose** — for MongoDB
- **Java 21** — for the Spring Boot backend (use [SDKMAN](https://sdkman.io/) or [Homebrew](https://brew.sh/))
- **Gradle** (or use the included `./gradlew` wrapper) — the backend build tool
- **Python 3.12+** — for the AI service
- **Node.js 20+** and **npm** — for the frontend
- API keys and credentials:
  - **OpenAI API key** or **Google Gemini API key** (for LLM calls in the AI service)
  - **GitHub personal access token** (for GitHub API sourcing)

---

### Step 1 — Start MongoDB

From the repo root:

```bash
docker-compose up -d
```

This starts MongoDB on port `27017` (credentials: `root` / `root`, database: `talentlens`).

---

### Step 2 — Start the AI Service

```bash
cd talentlens-ai
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `talentlens-ai/` with:

```
OPENAI_API_KEY=your_openai_key          # or GEMINI_API_KEY for Gemini
LLM_PROVIDER=openai                     # or gemini
GITHUB_TOKEN=your_github_token
MONGODB_URI=mongodb://root:root@localhost:27017/talentlens?authSource=admin
```

Then start the service:

```bash
uvicorn app.main:app --reload --port 8000
```

The AI service will be available at `http://localhost:8000`.

---

### Step 3 — Start the Backend

```bash
cd talentlens-backend
```

Create `src/main/resources/application-dev.yml` (or set environment variables) with:

```
MONGODB_URI=mongodb://root:root@localhost:27017/talentlens?authSource=admin
AI_SERVICE_URL=http://localhost:8000
JWT_SECRET=a-long-random-secret-string-at-least-32-characters
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Then start the backend:

```bash
./gradlew bootRun
```

The backend will be available at `http://localhost:8080`.

---

### Step 4 — Start the Frontend

```bash
cd talentlens-client
npm install
```

Create a `.env.local` file in `talentlens-client/` with:

```
VITE_API_BASE_URL=http://localhost:8080
```

Then start the dev server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

### Service Summary

| Service | URL | Notes |
|---|---|---|
| Frontend | `http://localhost:3000` | Vite dev server |
| Backend | `http://localhost:8080` | Spring Boot |
| AI Service | `http://localhost:8000` | FastAPI with `--reload` |
| MongoDB | `localhost:27017` | Via Docker |

---

### Running Tests

**Backend:**
```bash
cd talentlens-backend
./gradlew test          # unit tests
./gradlew verify        # full test suite including integration tests
```

**AI Service:**
```bash
cd talentlens-ai
source venv/bin/activate
pytest
```

**Frontend:**
```bash
cd talentlens-client
npm test
```
