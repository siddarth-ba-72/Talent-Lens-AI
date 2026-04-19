# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This is a **specification-only repository** — no implementation code exists yet. All architecture and requirements are documented in `specs/` and `requirements/`. Implementation follows the planned directory layout below.

## Architecture Overview

TalentLens is a multi-service AI-powered recruiter tool that sources and scores candidates from GitHub and Stack Overflow based on job descriptions.

**Three services** communicate via REST (synchronous) and Kafka (asynchronous):

```
talentlens-ui/        # React 18 + TypeScript + Vite + Tailwind CSS → Vercel
talentlens-backend/   # Java 17 + Spring Boot 3 + Spring Security → Render
talentlens-ai/        # Python 3.11 + FastAPI + LangChain/LangGraph → Render
```

**Infrastructure:** MongoDB Atlas (data), Confluent Cloud Kafka (async messaging), Docker Compose (local dev).

### Key Data Flow

**JD Parsing (sync):**
Frontend → Backend (REST) → AI Service `/ai/parse-jd` → MongoDB → response

**Candidate Sourcing (async via Kafka):**
Frontend triggers → Backend publishes to `sourcing-requests` topic → AI Service consumes → queries GitHub/SO APIs → LLM scores candidates → writes to MongoDB → publishes to `sourcing-results` topic → Backend updates task status → Frontend polls `/api/searches/{id}/source-status`

### Roles
- `RECRUITER`: full access (create/delete searches, trigger sourcing, export candidates)
- `HIRING_MANAGER`: read-only access (view and export candidates only)

## Commands

These commands apply once implementation is underway. The directory structure is per the planned layout.

### Frontend (`talentlens-ui/`)
```bash
npm install
npm run dev          # Vite dev server — http://localhost:3000
npm run build
npm run lint
npm run type-check
npm test
```

### Backend (`talentlens-backend/`)
```bash
mvn clean install
mvn spring-boot:run  # http://localhost:8080
mvn test
mvn verify           # full test suite
```

### AI Service (`talentlens-ai/`)
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload  # http://localhost:8000
pytest
black .
flake8
```

### Full Local Stack
```bash
docker-compose up    # MongoDB + Kafka + all services
docker-compose down
```

## Environment Variables

| Service | Key Variables |
|---------|--------------|
| Backend | `MONGODB_URI`, `AI_SERVICE_URL`, `KAFKA_BOOTSTRAP_SERVERS`, `JWT_SECRET` |
| AI Service | `OPENAI_API_KEY`, `GITHUB_TOKEN`, `MONGODB_URI`, `KAFKA_BOOTSTRAP_SERVERS` |
| Frontend | `VITE_API_BASE_URL=http://localhost:8080/api` |

## LLM Usage

- **JD parsing & query generation:** GPT-4o-mini, temperature 0.0, Pydantic output parsers
- **Candidate scoring:** GPT-4o, LangGraph multi-step agent, batched 5 candidates/call, asyncio for parallelism
- Estimated cost: ~$0.15 per search

## API Surface

All routes are under `/api/`. Auth routes are public; all others require JWT.

- `POST /api/auth/register|login|refresh`, `GET /api/auth/me`
- `POST /api/searches`, `GET /api/searches`, `GET /api/searches/{id}`, `DELETE /api/searches/{id}`
- `POST /api/searches/{id}/source`, `GET /api/searches/{id}/source-status`
- `GET /api/searches/{id}/candidates`, `GET /api/searches/{id}/candidates/export`
- Internal (backend → AI only): `POST /ai/parse-jd`, `POST /ai/generate-queries`

## Kafka Topics

- `sourcing-requests` — Backend → AI Service (trigger sourcing job)
- `sourcing-results` — AI Service → Backend (job completion/failure)

AI Service consumer retries with exponential backoff (max 3 attempts) on failure.

## Planned Source Layout

```
talentlens-backend/src/main/java/com/talentlens/
  config/          # Security, Kafka, CORS, Mongo configuration
  controller/      # Auth, Search, Candidate REST controllers
  service/         # Business logic + AI client + export
  repository/      # MongoDB repositories
  model/           # Document models
  dto/             # Request/response DTOs
  security/        # JWT filter + token utils
  kafka/           # Producer + consumer
  exception/       # GlobalExceptionHandler (@RestControllerAdvice)

talentlens-ai/app/
  api/             # FastAPI routers (jd_parser, query_generator)
  services/        # GitHub client, SO client, scoring service
  agents/          # LangChain chains, LangGraph scoring agent
  kafka/           # Consumer (sourcing-requests) + producer (sourcing-results)
  models/          # Pydantic schemas
  db/              # MongoDB client

talentlens-ui/src/
  api/             # Axios instance + API functions
  components/      # Reusable UI (CandidateCard, MatchScoreBadge, Pagination, etc.)
  pages/           # Login, Register, Dashboard, NewSearch, SearchDetail
  hooks/           # useAuth, useSearches, useSearch, useCandidates, useSourcingStatus, useExport
  context/         # AuthContext
  types/           # TypeScript interfaces
```

## Specification Files

- `specs/TalentLens-Architecture-Design.md` — Full technical design (MongoDB schema, Kafka message schemas, complete API contracts, deployment, NFRs)
- `requirements/candidate-sourcing-tool-requirements.md` — Product requirements and user stories
