# TalentLens - Phase 2: GenAI / LLM Service Specification

---

## 1. Phase 2 Objective

Phase 2 delivers the Python FastAPI AI service that powers:

1. JD parsing into structured JSON (returned to Spring Boot)
2. Candidate sourcing and deterministic ranking pipeline (results returned to Spring Boot for persistence)
3. Re-runnable sourcing for the same search with unique `runId` per run and persistent run history

Spring Boot remains the system of record for candidate persistence and task state updates.

Each run must return only the top 20 ranked candidates; backend persists those top 20 for that run.

---

## 2. Scope and Non-Scope

### In Scope

- FastAPI service in `talentlens-ai/`
- LangChain and LangGraph orchestration
- MCP-based external tool calling for sourcing
- Gemini-first model integration with OpenAI-ready abstraction
- Deterministic candidate ranking:
  - skill match weight = 60%
  - experience match weight = 40%
- Kafka-driven async sourcing flow aligned with Phase 1 backend
- Support repeated sourcing for the same search while preserving all `runId` records
- AI returns top 20 ranked candidates per run (hard cap)
- Minimal internal REST endpoint for manual/debug sourcing invocation

### Out of Scope

- Frontend implementation changes
- ATS integrations and outreach automation
- Non-public profile scraping or private data sources

---

## 3. Architecture Decisions for Phase 2

### 3.1 Source of Truth

- Backend persists candidates
- AI service does not write candidates to MongoDB in Phase 2

### 3.2 Orchestration Pattern

- Keep async sourcing via Kafka:
  - Backend publishes to `sourcing-requests`
  - AI consumes request, runs sourcing chain, publishes result payload to `sourcing-results`
  - Backend consumes results and saves candidates
- Add a minimal internal debug endpoint (`POST /ai/source-candidates`) that reuses the same sourcing pipeline; production backend flow remains Kafka-first

### 3.3 LLM Provider Strategy

- Default provider: Gemini
- Secondary provider: OpenAI (implemented in Phase 2)
- Provider selected by config, not hardcoded
- No feature flags for provider availability; runtime selection is environment-driven

### 3.4 Determinism Strategy

- LLM calls with deterministic settings (`temperature=0`, fixed prompt templates)
- Final ranking score computed by deterministic Python formula
- Stable tie-breaker ordering applied after scoring

### 3.5 Run History and Re-run Semantics

- A single search can execute sourcing multiple times
- Each sourcing execution gets a unique `runId`
- Backend persists all runs and all run identifiers (no overwrite of prior runs)
- Candidate dedupe is scoped to (`searchId`, `runId`, `source`, `sourceUsername`)

---

## 4. Target Tech Stack

- Python 3.11+
- FastAPI
- LangChain
- LangGraph
- Pydantic v2
- Confluent Kafka client (or aiokafka)
- MCP clients for external tool calls

---

## 5. Service Contracts

## 5.1 Synchronous Parsing APIs

### POST `/ai/parse-jd`

Request:

```json
{
  "jdText": "string"
}
```

Response:

```json
{
  "skills": ["string"],
  "responsibilities": ["string"],
  "experienceLevel": "string",
  "qualifications": ["string"],
  "technologies": ["string"],
  "domain": "string",
  "summary": "string"
}
```

### POST `/ai/parse-jd-file`

- Multipart field: `jdFile`
- AI service performs file extraction and parsing
- Returns same structured schema as `/ai/parse-jd`

## 5.2 Asynchronous Sourcing Contracts

### Consume: `sourcing-requests`

Input (from backend):

```json
{
  "taskId": "string",
  "searchId": "string",
  "runId": "string",
  "parsedJd": {
    "skills": ["string"],
    "responsibilities": ["string"],
    "experienceLevel": "string",
    "qualifications": ["string"],
    "technologies": ["string"],
    "domain": "string",
    "summary": "string"
  },
  "platforms": ["GITHUB", "STACKOVERFLOW", "LEETCODE", "PEOPLES_DATA"],
  "timestamp": "ISO-8601"
}
```

### Produce: `sourcing-results`

Output (AI -> backend):

```json
{
  "taskId": "string",
  "searchId": "string",
  "runId": "string",
  "status": "COMPLETED | FAILED",
  "candidatesFound": 0,
  "candidates": [
    {
      "name": "string",
      "email": "string|null",
      "avatarUrl": "string|null",
      "profileUrl": "string",
      "source": "GITHUB|STACKOVERFLOW|LEETCODE|PEOPLES_DATA|OTHER",
      "sourceUsername": "string",
      "skills": ["string"],
      "bio": "string|null",
      "location": "string|null",
      "experience": "string|null",
      "matchScore": 0,
      "scoreBreakdown": {
        "skillMatch": 0,
        "experienceMatch": 0,
        "overallFit": 0
      },
      "sourcedAt": "ISO-8601"
    }
  ],
  "error": "string|null",
  "completedAt": "ISO-8601"
}
```

Contract rules:

- AI must echo the incoming `runId` exactly in the result message
- AI must return at most 20 candidates in `candidates[]`
- `candidatesFound` equals `candidates[].length` and is therefore in range [0, 20]
- Backend must persist `candidates[]` for `searchId` and `runId`

## 5.3 Internal Debug Endpoint (Minimal Effort)

### POST `/ai/source-candidates`

- Purpose: manual/debug invocation of the same sourcing pipeline used by Kafka consumers
- Usage: local testing and diagnostics only
- Production backend integration remains Kafka-first

Request body: same schema as `sourcing-requests` payload.

Response body: same schema as `sourcing-results` payload.

---

## 6. LangGraph Pipeline Design (Sourcing)

State graph nodes:

1. `build_queries`
2. `source_candidates`
3. `normalize_profiles`
4. `score_candidates`
5. `rank_candidates`
6. `publish_results`

Node details:

- `build_queries`
  - uses parsed JD to produce platform-specific query plans
- `source_candidates`
  - invokes MCP tools for GitHub/StackOverflow/LeetCode and optional People Data adapter
- `normalize_profiles`
  - converts heterogeneous platform outputs to a canonical candidate schema
- `score_candidates`
  - computes `skillMatch` and `experienceMatch`
- `rank_candidates`
  - computes deterministic final score and ordering
  - enforces top 20 cap after deterministic sorting
- `publish_results`
  - emits result payload to Kafka

---

## 7. Deterministic Scoring and Ranking

## 7.1 Weighted Formula

Let:

- `S` = skill match score in range [0, 100]
- `E` = experience match score in range [0, 100]

Final score:

$$
\text{matchScore} = \text{round}(0.6 \times S + 0.4 \times E, 2)
$$

## 7.2 Determinism Rules

- LLM prompts and schemas are fixed and versioned
- `temperature = 0`
- No random sampling in ranking logic
- Stable tie-break order:
  1. higher `matchScore`
  2. higher `skillMatch`
  3. source priority (`GITHUB`, `STACKOVERFLOW`, then others)
  4. lexicographic `sourceUsername`

## 7.3 Scoring Implementation Rule

- Ranking math is pure Python (not delegated to LLM)
- LLM may assist with structured extraction/normalization only

---

## 8. MCP Tool Integration Plan

Required MCP-backed tools:

- GitHub toolset:
  - user search
  - profile fetch
  - repositories/languages fetch
- StackOverflow toolset:
  - user/tag search
  - profile/top-tags fetch
- LeetCode toolset:
  - user search/profile fetch
  - solved problems and language stats fetch

Optional future toolsets:

- People Data connector
- GitLab public profiles
- Kaggle public profiles
- Dev.to public profiles

MCP integration guidelines:

- use tool wrappers behind `SourceToolAdapter` interface
- enforce request throttling and retries
- normalize tool responses to a canonical schema before scoring

---

## 9. Provider Abstraction (Gemini First, OpenAI Ready)

## 9.1 Interface

Define provider abstraction:

- `LlmProvider` interface with methods for:
  - structured extraction
  - query generation
  - profile normalization

Implementations:

- `GeminiProvider` (default)
- `OpenAiProvider` (fully implemented in Phase 2)

## 9.2 Runtime Config

Environment variables:

- `LLM_PROVIDER=gemini|openai` (default: `gemini`)
- `GEMINI_API_KEY` (required when provider is `gemini`)
- `OPENAI_API_KEY` (required when provider is `openai`)
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`

## 9.3 Prompt and Schema Compatibility

- Provider-neutral prompt templates
- Pydantic output schemas shared by both providers
- Contract tests validate equivalent schema output across providers

---

## 10. Data Models (AI Service)

Core Pydantic models:

- `ParsedJdModel`
- `QueryPlanModel`
- `RawCandidateModel`
- `NormalizedCandidateModel`
- `RankedCandidateModel`
- `SourcingResultPayloadModel`

All outbound payloads must be schema-validated before publish.

---

## 11. Backend Impact Required for Phase 2

Backend updates required to complete Phase 2 integration:

1. Extend `SourcingResultMessage` to include `candidates[]` (max size 20)
2. Update `SourcingResultConsumer` to persist candidates for `searchId` and `runId`
3. Persist all run records for a search (full run history) via `SourcingTask` and `runId`
4. Keep existing status and `candidateCount` update logic
5. Keep dedupe with unique index (`searchId`, `runId`, `source`, `sourceUsername`)
6. Expand allowed source platforms to include `LEETCODE` (and `PEOPLES_DATA` if enabled)

---

## 12. Reliability, Safety, and Observability

- Retry policy for external tool calls with bounded attempts
- Partial-failure handling by platform (continue when one platform fails)
- Structured logs with correlation keys: `taskId`, `searchId`, `runId`
- Metrics:
  - parse latency
  - sourcing latency
  - provider token/latency usage
  - candidates sourced per platform
- Never fabricate candidate identity or contact details

---

## 13. Testing Strategy for Phase 2

1. Unit tests
- parsing output schema validation
- scoring and ranking determinism
- provider adapter behavior

2. Integration tests
- `/ai/parse-jd` and `/ai/parse-jd-file`
- `/ai/source-candidates` debug endpoint
- Kafka consume-process-produce flow
- MCP tool adapter integration with mocked tool responses

3. Contract tests with backend
- `sourcing-requests` input schema compatibility
- `sourcing-results` output schema compatibility

4. Regression tests
- fixed fixture inputs must produce stable ranking order across runs
- repeated sourcing runs for the same `searchId` must preserve distinct `runId`s and persisted history
- each run output must never exceed top 20 candidates

---

## 14. Implementation Milestones

### M1: Foundation

- FastAPI skeleton
- provider abstraction + Gemini provider
- parse endpoints and schemas

### M2: Sourcing Chain

- LangGraph pipeline
- MCP adapters for GitHub, StackOverflow, and LeetCode
- deterministic scoring module
- top 20 truncation after ranking

### M3: Kafka Integration

- consume `sourcing-requests`
- produce enriched `sourcing-results` with candidates
- retry/error handling

### M4: Hardening

- OpenAI provider parity and runtime selection validation
- observability dashboards/logging polish
- end-to-end contract verification with backend

---

## 15. Deliverables Checklist

- `talentlens-ai` FastAPI service scaffold
- Provider abstraction (`GeminiProvider`, `OpenAiProvider`)
- LangGraph sourcing workflow with MCP tools
- Deterministic ranking implementation (60/40)
- Parse endpoints (`/ai/parse-jd`, `/ai/parse-jd-file`)
- Internal debug endpoint (`/ai/source-candidates`)
- Kafka consumer/producer integration for sourcing
- Structured result payload including ranked candidates
- Top 20 return cap enforced at AI output boundary
- Multi-run history support with persistent `runId` tracking
- Test suite (unit + integration + contract)
- Runbook for local and production deployment

---

## 16. Confirmed Product Decisions

1. Sourcing remains Kafka-first; a minimal internal REST debug endpoint is also included.
2. AI returns only top 20 candidates per run; backend persists those top 20.
3. Phase 2 platform scope includes GitHub, StackOverflow, and LeetCode, with optional People Data connector.
4. Deterministic tie-break order is approved as defined in Section 7.2.
5. OpenAI support is implemented in Phase 2 (not feature-flag gated).
6. Result delivery remains Kafka publish from AI to backend.
7. Re-running sourcing on the same search is supported; all `runId`s are persisted.
