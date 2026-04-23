# TalentLens — Phase 1: Spring Boot Backend Specification

---

## 1. Scope of Phase 1

Phase 1 delivers the complete Spring Boot backend service. At the end of this phase, the backend must be:

- Fully functional for auth, search CRUD, candidate management, and export
- Fully functional for search sharing workflow: hiring manager request, recruiter approve/reject, and persisted request history
- Publishing to the `sourcing-requests` Kafka topic and consuming from `sourcing-results` (AI service is not live yet — integration is wired and testable with a local Kafka and a manual test consumer)
- Calling the AI service synchronously for JD parsing and file forwarding (tested against a WireMock stub; will connect to the live Phase 2 AI service with zero backend changes)
- Running locally via `docker-compose` with MongoDB and Kafka
- Covered by unit tests on the service layer and integration tests on controller endpoints

Phase 1 does **not** implement: the Python AI service, LLM calls, GitHub/SO sourcing, or the React frontend.

---

## 2. Technology Stack

| Concern | Library / Version |
|---|---|
| Language | Java 17 (LTS) |
| Framework | Spring Boot 3.2.x |
| Security | Spring Security 6 |
| Data | Spring Data MongoDB |
| Messaging | Spring Kafka |
| HTTP Client | Spring WebFlux `WebClient` (non-blocking AI service calls) |
| Validation | Jakarta Bean Validation 3 |
| JWT | `io.jsonwebtoken:jjwt` 0.12.x |
| Build | Maven 3.9+ |
| Testing | JUnit 5, Mockito, Spring Boot Test, Testcontainers (MongoDB), WireMock, EmbeddedKafka |
| Code Generation | Lombok, MapStruct |

**Why these choices:**

- `WebClient` over `RestTemplate`: non-blocking I/O frees the thread while waiting for the AI service, which is important for free-tier hosting with a limited thread pool and a 30-second AI parsing call.
- `jjwt 0.12.x`: actively maintained with explicit algorithm specification — avoids the `none` algorithm vulnerability present in older JWT libraries.
- Testcontainers: integration tests run against a real MongoDB container rather than mocks, preventing mock/real divergence that could mask bugs at the data layer.
- MapStruct: compile-time DTO mapping with no reflection overhead and compile errors on missing fields, rather than runtime mapping frameworks.
- No Apache PDFBox or Apache POI: file text extraction is delegated entirely to the AI service (see Section 6.4).

---

## 3. Maven Dependency Groups (`pom.xml`)

The following dependency groups are required. Exact artifact coordinates are resolved during implementation.

**Core Web and Security:** `spring-boot-starter-web`, `spring-boot-starter-security`, `spring-boot-starter-validation`, `spring-boot-starter-actuator`

**Data and Messaging:** `spring-boot-starter-data-mongodb`, `spring-boot-starter-webflux` (for WebClient), `spring-kafka`

**JWT:** `jjwt-api`, `jjwt-impl` (runtime), `jjwt-jackson` (runtime) — all at version 0.12.x

**Code Generation (provided/annotation-processor scope):** `lombok`, `mapstruct`, `mapstruct-processor`

**Testing (test scope):** `spring-boot-starter-test`, `spring-kafka-test` (EmbeddedKafka), `testcontainers:mongodb`, WireMock standalone

---

## 4. Application Configuration (`application.yml`)

Configuration is split into a base profile (local dev) and a `prod` profile (Render + Confluent Cloud).

**Base profile settings:**
- MongoDB URI from `MONGODB_URI` env var, defaulting to `localhost:27017/talentlens`
- Kafka bootstrap servers from `KAFKA_BOOTSTRAP_SERVERS`, defaulting to `localhost:9092`
- Kafka producer serialises values as JSON; consumer deserialises from JSON, trusting only the `com.talentlens.kafka.dto` package
- Multipart max file size: 5MB; max request size: 6MB
- JWT secret, access token expiry (900,000 ms / 15 min), refresh token expiry (604,800,000 ms / 7 days) all from env vars
- AI service base URL from `AI_SERVICE_URL`, defaulting to `http://localhost:8000`, with a 30-second timeout
- CORS allowed origins from `CORS_ALLOWED_ORIGINS`, defaulting to `http://localhost:3000`
- Kafka topic names for `sourcing-requests` and `sourcing-results` configured as app properties (not hardcoded in Java)

**Production profile additions:**
- Kafka SASL/SSL configuration for Confluent Cloud (`KAFKA_SASL_USERNAME`, `KAFKA_SASL_PASSWORD`, `KAFKA_SECURITY_PROTOCOL=SASL_SSL`, `KAFKA_SASL_MECHANISM=PLAIN`)

---

## 5. Package Architecture

The package layout follows a **layered architecture** — each layer is a top-level package; classes within it are organised by domain concept.

```
com.talentlens/
├── TalentLensApplication.java

├── config/
│   ├── SecurityConfig.java
│   ├── KafkaConfig.java
│   ├── MongoConfig.java
│   └── WebClientConfig.java

├── controller/
│   ├── AuthController.java
│   ├── SearchController.java
│   ├── CandidateController.java
│   └── ShareRequestController.java

├── service/
│   ├── AuthService.java                  (interface)
│   ├── SearchService.java                (interface)
│   ├── CandidateService.java             (interface)
│   ├── ShareRequestService.java          (interface)
│   ├── SourcingService.java              (interface)
│   ├── AiServiceClient.java              (interface)
│   ├── ExportService.java                (interface)
│   └── impl/
│       ├── AuthServiceImpl.java
│       ├── SearchServiceImpl.java
│       ├── CandidateServiceImpl.java
│       ├── ShareRequestServiceImpl.java
│       ├── SourcingServiceImpl.java
│       ├── AiServiceClientImpl.java
│       ├── CsvExportService.java
│       └── JsonExportService.java

├── repository/
│   ├── UserRepository.java
│   ├── SearchRepository.java
│   ├── SearchRepositoryCustom.java       (interface)
│   ├── SearchRepositoryCustomImpl.java
│   ├── CandidateRepository.java
│   ├── CandidateRepositoryCustom.java    (interface)
│   ├── CandidateRepositoryCustomImpl.java
│   ├── SourcingTaskRepository.java
│   └── ShareRequestRepository.java

├── model/
│   ├── User.java
│   ├── Search.java
│   ├── Candidate.java
│   ├── SourcingTask.java
│   ├── ShareRequest.java
│   └── embedded/
│       ├── ParsedJd.java
│       └── ScoreBreakdown.java

├── dto/
│   ├── request/
│   │   ├── LoginRequest.java
│   │   ├── RegisterRequest.java
│   │   ├── RefreshTokenRequest.java
│   │   └── SourcingRequest.java
│   └── response/
│       ├── AuthResponse.java
│       ├── UserResponse.java
│       ├── SearchResponse.java
│       ├── SearchSummaryResponse.java
│       ├── CandidateResponse.java
│       ├── SourcingStatusResponse.java
│       ├── ShareRequestResponse.java
│       └── PageResponse.java

├── mapper/
│   ├── SearchMapper.java
│   ├── CandidateMapper.java
│   └── ShareRequestMapper.java

├── security/
│   ├── JwtTokenProvider.java
│   ├── JwtAuthenticationFilter.java
│   └── UserDetailsServiceImpl.java

├── kafka/
│   ├── dto/
│   │   ├── SourcingRequestMessage.java
│   │   └── SourcingResultMessage.java
│   ├── SourcingRequestProducer.java
│   └── SourcingResultConsumer.java

└── exception/
    ├── GlobalExceptionHandler.java
    ├── ResourceNotFoundException.java
    ├── UnauthorizedException.java
    ├── ForbiddenException.java
    ├── AiServiceException.java
    ├── DuplicateResourceException.java
    ├── InvalidFileException.java
    └── ErrorResponse.java
```

---

## 6. Design Principles and Patterns

### 6.1 Layered Architecture with Dependency Inversion

The strict dependency direction is: Controller → Service Interface ← Service Impl → Repository Interface ← Spring Data Impl. Controllers depend on service interfaces only. Service implementations depend on repository interfaces only. No layer reaches across to another layer's implementation directly. This makes each layer independently testable by substituting the dependency with a mock.

### 6.2 Service Interface Pattern

Every service is declared as a Java interface that defines the contract. The controller injects the interface; Spring wires the implementation at runtime. This pattern makes unit-testing controllers trivial (mock the interface with Mockito) and leaves open the possibility of swapping implementations without touching controllers.

### 6.3 Strategy Pattern — Export Service

The export format (CSV or JSON) is a runtime decision based on the `format` query parameter. Rather than branching in the controller, a factory resolves the correct `ExportService` implementation by format string. Both implementations share the same interface contract. The controller is unaware of which format is active. New export formats can be added without modifying the controller or factory.

### 6.4 Facade Pattern — AI Service Client

`AiServiceClient` is a facade that hides all WebClient complexity, HTTP error mapping, timeout configuration, and response deserialisation from the service layer. The service layer calls a single method and receives a typed result (`ParsedJd`). The service layer never sees HTTP status codes or WebClient internals.

The interface exposes two methods:
- One that accepts raw JD text (for the paste flow) and calls `POST /ai/parse-jd`
- One that accepts a raw multipart file and forwards it to `POST /ai/parse-jd-file` (for the file upload flow)

Text extraction from PDF/DOCX/TXT is **not performed in the backend**. Spring Boot receives the file and forwards the raw bytes to the AI service as a multipart request. The AI service is responsible for extraction and parsing. This removes Apache PDFBox and Apache POI as backend dependencies and keeps all file-handling intelligence in the AI layer.

### 6.5 Repository Custom Fragment Pattern

Spring Data MongoDB repositories handle simple CRUD and single-field lookups. Complex queries — dynamic filtering with multiple optional parameters, compound sorting, pagination — are handled by a custom repository fragment. Each repository that needs dynamic querying declares a `Custom` interface and a corresponding `CustomImpl` that uses `MongoTemplate` with a programmatic `Criteria` builder. Spring Data wires both together automatically when the main repository interface extends both the `MongoRepository` and the `Custom` interface.

### 6.6 DTO Pattern with MapStruct

Domain models (`@Document` classes) are never returned directly from controllers. Every controller returns a DTO. MapStruct generates type-safe mapping code at compile time based on interface declarations. Compile errors are raised for missing or mismatched fields, preventing silent data leaks or missing fields at runtime.

Request DTOs use Lombok `@Data` with Jakarta validation annotations. Response DTOs use Java 17 records (immutable, no setters needed).

### 6.7 Multi-threading Design

The following threading decisions are intentional:

**JD parsing AI call:** `WebClient` is used with `.block()` for the synchronous JD parsing call. The user is waiting for this response (the UI does not move on until parsing completes), so blocking is semantically correct. WebClient's non-blocking transport still frees the Netty thread during the wait — the blocking happens on the calling thread only, not on the I/O thread. At MVP scale (10-20 users), this is perfectly acceptable.

**Kafka consumer:** Spring Kafka's `@KafkaListener` runs on a dedicated listener thread pool, completely isolated from the Tomcat HTTP thread pool. Sourcing result processing is fast (two MongoDB writes), so the default single-listener-thread-per-partition configuration is sufficient for MVP.

**Kafka producer:** The producer's `send()` call is awaited before returning 202 to the client. This confirms the message was durably enqueued before the recruiter sees the "sourcing started" response. If Kafka is unreachable, the recruiter gets a 503, not a silent failure.

**Export streaming:** The export endpoints write directly to `HttpServletResponse.getOutputStream()` row-by-row (CSV) or element-by-element (JSON array). No intermediate collection is built in memory. This keeps heap pressure flat regardless of how many candidates are exported.

---

## 7. Domain Models

All models are MongoDB `@Document` classes. Field names are camelCase matching MongoDB BSON directly. Indexes are declared programmatically in `MongoConfig` on application startup (auto-index-creation is disabled to avoid startup latency in production).

### 7.1 User

Fields: `id`, `email` (unique indexed), `password` (BCrypt hashed), `name`, `role` (enum: `RECRUITER` | `HIRING_MANAGER`), `createdAt`, `updatedAt`.

### 7.2 Search

Fields: `id`, `userId` (indexed), `title` (auto-derived from JD summary on creation), `rawJdText`, `jdFileName` (nullable — populated only when a file was uploaded), `parsedJd` (embedded subdocument), `sourcingStatus` (enum: `IDLE` | `IN_PROGRESS` | `COMPLETED` | `FAILED`), `sourcingPlatforms` (list of strings), `candidateCount` (running total of active candidates across all sourcing runs), `sharedWith` (list of userId strings — hiring managers explicitly granted access), `createdAt`, `updatedAt`.

Indexes: `{ userId: 1 }`, `{ userId: 1, createdAt: -1 }`, `{ sharedWith: 1 }`.

### 7.3 ParsedJd (Embedded Subdocument)

Not a standalone collection. Embedded directly inside `Search`. Fields: `skills` (list), `responsibilities` (list), `experienceLevel` (string), `qualifications` (list), `technologies` (list), `domain` (string), `summary` (string).

### 7.4 Candidate

Fields: `id`, `searchId` (indexed), `runId` (the sourcing run that found this candidate — see Section 8.3), `name`, `email` (nullable), `avatarUrl` (nullable), `profileUrl`, `source` (enum: `GITHUB` | `STACKOVERFLOW`), `sourceUsername`, `skills` (list), `bio` (nullable), `location` (nullable), `experience` (nullable), `matchScore` (0–100), `scoreBreakdown` (embedded), `isActive` (boolean — false when soft-deleted), `sourcedAt`, `createdAt`.

Indexes:
- `{ searchId: 1, runId: 1, source: 1, sourceUsername: 1 }` — unique compound index for deduplication within a run
- `{ searchId: 1, isActive: 1, matchScore: -1 }` — primary query index for candidate listing

### 7.5 ScoreBreakdown (Embedded Subdocument)

Fields: `skillMatch` (0–100), `experienceMatch` (0–100), `overallFit` (0–100).

### 7.6 SourcingTask

Fields: `id`, `searchId` (indexed), `runId` (matches the `runId` on all candidates from this run — timestamp-based string, e.g. `run_20260419_143022`), `platforms` (list), `status` (enum: `PENDING` | `IN_PROGRESS` | `COMPLETED` | `FAILED`), `candidatesFound`, `error` (nullable), `startedAt`, `completedAt` (nullable).

Indexes: `{ searchId: 1 }`, `{ status: 1 }`.

### 7.7 ShareRequest

Fields: `id`, `searchId` (indexed), `requesterUserId` (indexed), `ownerUserId` (indexed), `status` (enum: `PENDING` | `APPROVED` | `REJECTED`), `requestedAt`, `resolvedAt` (nullable), `resolvedBy` (nullable), `note` (nullable).

Indexes:
- `{ ownerUserId: 1, status: 1, requestedAt: -1 }`
- `{ requesterUserId: 1, requestedAt: -1 }`
- `{ searchId: 1, requesterUserId: 1, status: 1 }`

---

## 8. Re-Search and Run-ID Design

### 8.1 Purpose

Each time a recruiter triggers candidate sourcing (initial or re-search), a distinct sourcing run is recorded. Runs are isolated snapshots: the same candidate profile can appear in two different runs for the same search if they were found at different times. This preserves the historical record of who was found in each run rather than overwriting or merging results.

### 8.2 Run ID Format

The `runId` is a human-readable, timestamp-based string generated at the moment sourcing is triggered: `run_<yyyy-MM-dd>_<HH-mm-ss>` in UTC. Example: `run_2026-04-19_143022`. This makes it immediately meaningful when displayed or queried — a recruiter or developer can see at a glance when a run occurred.

### 8.3 Candidate Association

Every candidate written by the AI service carries both `searchId` and `runId`. The deduplication unique index is scoped to `{ searchId, runId, source, sourceUsername }` — deduplication applies within a run only. The same GitHub username can appear in run A and run B if they are found again.

### 8.4 Candidate Count

`search.candidateCount` is a cumulative counter. When the `SourcingResultConsumer` processes a completed run, it increments `candidateCount` by `candidatesFound` from that run. This is an approximation — it does not subtract soft-deleted candidates. The precise active count for a given run or across all runs can always be computed with a repository count query; the field provides a fast summary for the dashboard card.

### 8.5 Run ID in Kafka Messages

The `runId` is included in both the `SourcingRequestMessage` (backend → AI service) and the `SourcingResultMessage` (AI service → backend). The AI service uses the `runId` from the request message to tag all candidates it writes to MongoDB for that run.

---

## 9. Security Architecture

### 9.1 Filter Chain

Spring Security 6 uses lambda-style configuration. The filter order for every request is:

1. CORS filter — validates origin and sets response headers
2. `JwtAuthenticationFilter` — extracts and validates JWT from the `Authorization: Bearer` header; populates the SecurityContext
3. Authorization filter — enforces role-based access control per endpoint
4. Controller

Session management is stateless (no server-side session). CSRF protection is disabled (JWT-authenticated REST API, no session cookies).

### 9.2 Endpoint Access Rules

| Endpoint Pattern | Access Rule |
|---|---|
| `POST /api/auth/**` | Public (no auth) |
| `GET /actuator/health` | Public |
| `POST /api/searches` | RECRUITER role only |
| `DELETE /api/searches/**` | RECRUITER role only |
| `POST /api/searches/*/source` | RECRUITER role only |
| `DELETE /api/searches/*/candidates/**` | RECRUITER role only |
| `GET /api/share-requests/recruiters` | HIRING_MANAGER role only |
| `POST /api/share-requests` | HIRING_MANAGER role only |
| `GET /api/share-requests/outgoing` | HIRING_MANAGER role only |
| `GET /api/share-requests/incoming` | RECRUITER role only |
| `POST /api/share-requests/*/approve` | RECRUITER role only |
| `POST /api/share-requests/*/reject` | RECRUITER role only |
| All other `/api/**` | Any authenticated user |

### 9.3 JWT Token Design

Two tokens are issued at login:

| Token | Purpose | Expiry | Claims |
|---|---|---|---|
| Access Token | Authenticate requests | 15 min | `sub` (userId), `email`, `role`, `iat`, `exp` |
| Refresh Token | Obtain a new access token | 7 days | `sub` (userId), `type: REFRESH`, `iat`, `exp` |

Refresh tokens are stateless — not stored in MongoDB. Revocation is not supported in MVP. When the refresh token expires, the user must log in again.

The JWT secret key minimum length is enforced programmatically at startup. Algorithm is explicitly specified as HS256 with a 256-bit key — the `none` algorithm is not accepted.

### 9.4 JwtAuthenticationFilter

On each request, the filter extracts the `Authorization: Bearer <token>` header, validates the signature and expiry using `JwtTokenProvider`, then builds a `UsernamePasswordAuthenticationToken` with the userId and role extracted from claims. This is set on the `SecurityContextHolder`. The filter does not make a database call — it trusts the JWT signature. This is why access tokens are kept short-lived.

### 9.5 Ownership Enforcement

Role-based access (RECRUITER vs HIRING_MANAGER) is enforced at the filter/authorization layer. Resource ownership is enforced in the service layer. For any write operation (delete search, trigger sourcing, soft-delete candidate), the service layer checks that the search's `userId` matches the authenticated user's ID and throws `ForbiddenException` (403) if not.

For HIRING_MANAGER access to a search, the service layer checks that the authenticated user's ID appears in the search's `sharedWith` list. A HIRING_MANAGER who is not in `sharedWith` receives a 404 (not 403 — the resource's existence is not revealed to unauthorised viewers).

### 9.6 Rate Limiting

A custom `OncePerRequestFilter` applied before the security chain protects `/api/auth/login` and `/api/auth/register` with a per-IP rate limit of 5 requests per 60-second window. On breach, the filter returns HTTP 429 with a `Retry-After` header. The window is tracked in-memory using a `ConcurrentHashMap`. This is appropriate for a single-instance free-tier deployment. A Redis-backed implementation would be required for multi-instance scale-out.

---

## 10. Controller Layer

Controllers are thin. Their only responsibilities are: deserialise and validate the request, extract the authenticated user's ID from the SecurityContext, delegate to the appropriate service method, and serialise the response. No business logic lives in controllers.

The authenticated user ID is extracted via a shared utility method that reads from `SecurityContextHolder` — controllers never parse JWTs directly.

### 10.1 AuthController — `/api/auth`

| Method | Path | Delegates To | Response Code |
|---|---|---|---|
| POST | `/register` | `AuthService.register` | 201 |
| POST | `/login` | `AuthService.login` | 200 |
| POST | `/refresh` | `AuthService.refresh` | 200 |
| GET | `/me` | `AuthService.getProfile` | 200 |

### 10.2 SearchController — `/api/searches`

| Method | Path | Delegates To | Response Code |
|---|---|---|---|
| POST | `/` | `SearchService.createSearch` | 201 |
| GET | `/` | `SearchService.listSearches` | 200 |
| GET | `/{id}` | `SearchService.getSearch` | 200 |
| DELETE | `/{id}` | `SearchService.deleteSearch` | 204 |
| POST | `/{id}/source` | `SourcingService.triggerSourcing` | 202 |
| GET | `/{id}/source-status` | `SourcingService.getStatus` | 200 |

`POST /` accepts `multipart/form-data` with either a `jdText` text field or a `jdFile` file field. A custom constraint annotation (`@ValidJdInput`) on the request wrapper enforces that exactly one of the two is present.

### 10.3 CandidateController — `/api/searches/{id}/candidates`

| Method | Path | Delegates To | Response Code |
|---|---|---|---|
| GET | `/` | `CandidateService.listCandidates` | 200 |
| DELETE | `/{candidateId}` | `CandidateService.softDelete` | 204 |
| GET | `/export` | `ExportServiceFactory` + chosen impl | 200 (file download) |

The export endpoint sets `Content-Disposition: attachment` and streams directly to `HttpServletResponse.getOutputStream()`. It does not return a body via the normal Spring MVC return value mechanism.

### 10.4 ShareRequestController — `/api/share-requests`

| Method | Path | Delegates To | Response Code |
|---|---|---|---|
| GET | `/recruiters` | `ShareRequestService.listRecruiters` | 200 |
| POST | `/` | `ShareRequestService.createRequest` | 201 |
| GET | `/incoming` | `ShareRequestService.listIncoming` | 200 |
| GET | `/outgoing` | `ShareRequestService.listOutgoing` | 200 |
| POST | `/{id}/approve` | `ShareRequestService.approve` | 200 |
| POST | `/{id}/reject` | `ShareRequestService.reject` | 200 |

---

## 11. Service Layer

### 11.1 AuthService

Responsibilities: validate registration input (duplicate email check → 409), hash password with BCrypt (strength 12), persist user, issue JWT pair on login, validate refresh token and issue new access token.

Login failure always returns 401 with a generic "invalid credentials" message — no hint about whether the email or password was wrong.

### 11.2 SearchService

**createSearch flow:**
1. Determine input type: if `jdFile` is present, call `aiServiceClient.parseJdFromFile(file)`; if `jdText` is present, call `aiServiceClient.parseJd(text)`. Both return a `ParsedJd`.
2. Derive `title` from `parsedJd.summary` (first 100 characters, truncated at a word boundary).
3. Build and persist a `Search` document with `sourcingStatus = IDLE`, `candidateCount = 0`.
4. Return `SearchResponse`.

**listSearches:** Delegates to `SearchRepositoryCustom.findWithFilters`. For RECRUITER role, filters by `userId`. For HIRING_MANAGER role, filters by `sharedWith contains userId`. Keyword filter uses case-insensitive regex on `title` and `rawJdText`. Supports sorting by `createdAt`, `candidateCount`, and `title`. Returns a `PageResponse<SearchSummaryResponse>`.

**getSearch:** Loads search by ID. Applies ownership or `sharedWith` check. Returns `SearchResponse` (full detail including `parsedJd`).

**deleteSearch:** Asserts ownership (RECRUITER only). Deletes in order: candidates by `searchId`, sourcing tasks by `searchId`, then the search document. Not wrapped in a transaction (MongoDB Atlas free tier has no multi-document transaction support). If a step fails, the search document remains and the delete can be retried.

### 11.3 SourcingService

**triggerSourcing flow:**
1. Load search, assert ownership.
2. Reject if `sourcingStatus = IN_PROGRESS` (prevents concurrent duplicate runs).
3. Generate `runId` as `run_<yyyy-MM-dd>_<HH-mm-ss>` in UTC.
4. Persist `SourcingTask` with `status = PENDING`, `runId`, `platforms`, `startedAt = now`.
5. Update `search.sourcingStatus = IN_PROGRESS`, persist.
6. Publish `SourcingRequestMessage` (containing `taskId`, `searchId`, `runId`, `parsedJd`, `platforms`, `timestamp`) to the `sourcing-requests` topic. Block until Kafka confirms delivery.
7. Return `SourcingStatusResponse { taskId, runId, status: PENDING }`.

**processSourcingResult (called by Kafka consumer):**
1. Load `SourcingTask` by `taskId`.
2. Update `status`, `candidatesFound`, `error`, `completedAt`.
3. Update `search.sourcingStatus` to `COMPLETED` or `FAILED`.
4. If `COMPLETED`, increment `search.candidateCount += candidatesFound`.
5. Persist both documents.

**getStatus:** Returns the most recent `SourcingTask` for the given `searchId` as a `SourcingStatusResponse`.

### 11.4 CandidateService

**listCandidates:** Delegates to `CandidateRepositoryCustom.findWithFilters`. Always filters `isActive = true`. Supports filtering by skills (any match in list), source (GITHUB/STACKOVERFLOW), match score range, and keyword (case-insensitive regex on name, bio, sourceUsername). Supports sorting by `matchScore` (default, descending), `name`, `sourcedAt`. Returns `PageResponse<CandidateResponse>`.

**softDelete:** Loads candidate by `id` and `searchId` (prevents cross-search access). Asserts the candidate's search is owned by the requester. Sets `isActive = false` and persists.

### 11.5 ExportService

Two implementations: `CsvExportService` and `JsonExportService`. Both implement `ExportService` with a `format()` method returning `"csv"` or `"json"`.

An `ExportServiceFactory` is injected with all `ExportService` implementations as a `Map<String, ExportService>` keyed by the return value of `format()`. The controller obtains the factory, resolves the implementation by the `format` query param, and delegates.

Both implementations: retrieve the full (un-paginated) candidate list via `CandidateRepositoryCustom.findAllWithFilters` (same filter logic as listing, `isActive = true` always), then stream the output field-by-field to `HttpServletResponse.getOutputStream()`. Headers (`Content-Type`, `Content-Disposition`, `filename`) are set before writing begins.

### 11.6 ShareRequestService

**createRequest flow (HIRING_MANAGER):**
1. Validate target search exists.
2. Validate requester is not the owner.
3. Validate owner role is `RECRUITER`.
4. Validate no existing pending request for `(searchId, requesterUserId)`.
5. Persist `ShareRequest` with `status = PENDING`.
6. Return `ShareRequestResponse`.

**approve flow (RECRUITER):**
1. Load request by ID and assert `ownerUserId` equals authenticated recruiter ID.
2. Ensure status is `PENDING`.
3. Update request to `APPROVED`, set `resolvedAt`, `resolvedBy`.
4. Add `requesterUserId` to `search.sharedWith` idempotently (no duplicates).
5. Persist request and search.

**reject flow (RECRUITER):**
1. Same ownership and state checks as approve.
2. Update request to `REJECTED`, set `resolvedAt`, `resolvedBy`.
3. Persist request only.

**listIncoming/listOutgoing:** paginated lists by owner/requester with optional status filter.

---

## 12. Repository Layer

### 12.1 UserRepository

Simple Spring Data repository. Key methods: find by email (for login and duplicate check), exists by email (for registration guard).

### 12.2 SearchRepository and SearchRepositoryCustom

The main repository extends both `MongoRepository` and `SearchRepositoryCustom`. The custom fragment provides `findWithFilters(userId, filterParams, pageable)` using `MongoTemplate` with a programmatic `Criteria` chain. Each filter parameter is conditionally added to the criteria only when it is non-null/non-empty — this produces a minimal query rather than an always-true base query with optional conditions.

Additional repository methods: find all by `userId` (for admin/debug use), delete by `userId`.

### 12.3 CandidateRepository and CandidateRepositoryCustom

The custom fragment provides two variants of the filter query: a paginated one (for listing) and an unpaginated one (for export). Both apply the same `Criteria` chain. The `findByIdAndSearchId` method on the main repository is used for ownership-scoped single-candidate lookups (prevents a candidate ID from one search being used against a different search).

`deleteBySearchId` is used during search cascade-delete.

### 12.4 SourcingTaskRepository

Key methods: find the most recent task for a given `searchId` (ordered by `startedAt` descending, limit 1), delete all tasks by `searchId`.

### 12.5 ShareRequestRepository

Key methods:
- Find pending requests by owner with pagination
- Find requests by requester with pagination
- Find by id and ownerUserId (ownership-scoped approval/rejection)
- Exists pending by searchId + requesterUserId (duplicate request guard)

---

## 13. Kafka Layer

### 13.1 Topic Configuration

Both topics (`sourcing-requests` and `sourcing-results`) are declared as Spring-managed `NewTopic` beans. Kafka auto-creates them on first use in local Docker mode. On Confluent Cloud they are pre-created via the Confluent UI before deployment.

Partition count: 1 (sufficient for MVP throughput). Replication factor: 1 (free-tier Kafka does not support higher replication).

### 13.2 Message Schemas

**SourcingRequestMessage** (backend → AI service, published to `sourcing-requests`):

| Field | Type | Description |
|---|---|---|
| `taskId` | string | SourcingTask `_id` |
| `searchId` | string | Search `_id` |
| `runId` | string | Timestamp-based run identifier |
| `parsedJd` | object | Full `ParsedJd` fields |
| `platforms` | list of strings | e.g. `["GITHUB", "STACKOVERFLOW"]` |
| `timestamp` | ISO-8601 string | When the message was produced |

**SourcingResultMessage** (AI service → backend, consumed from `sourcing-results`):

| Field | Type | Description |
|---|---|---|
| `taskId` | string | SourcingTask `_id` |
| `searchId` | string | Search `_id` |
| `runId` | string | Must match the run-id from the request |
| `status` | string | `COMPLETED` or `FAILED` |
| `candidatesFound` | integer | Number of candidates written to MongoDB |
| `error` | string or null | Error description on failure |
| `completedAt` | ISO-8601 string | When the AI service finished |

### 13.3 Producer Behaviour

`SourcingRequestProducer` uses `KafkaTemplate` with JSON serialisation. The message key is `searchId` (ensures all messages for a given search go to the same partition — ordering guaranteed per search). After calling `send()`, the producer awaits the resulting `CompletableFuture` to confirm broker acknowledgement before returning. A send failure throws a runtime exception that propagates to the controller, returning a 503.

### 13.4 Consumer Behaviour

`SourcingResultConsumer` is annotated with `@KafkaListener` bound to the `sourcing-results` topic. The listener runs on a dedicated Kafka listener thread, isolated from the HTTP thread pool. On receipt, it delegates to `SourcingService.processSourcingResult`. If processing throws an exception, it is caught and logged — the message is not retried (sourcing results are not replayable; the AI service handles its own retry before publishing a FAILED result).

---

## 14. Exception Handling

### 14.1 Exception Hierarchy

All domain exceptions extend `RuntimeException`. The hierarchy:

- `ResourceNotFoundException` → HTTP 404
- `UnauthorizedException` → HTTP 401
- `ForbiddenException` → HTTP 403
- `DuplicateResourceException` → HTTP 409
- `AiServiceException` → HTTP 503
- `InvalidFileException` → HTTP 400

Spring's built-in exceptions are also handled: `MethodArgumentNotValidException` → 400, `MaxUploadSizeExceededException` → 413, `AccessDeniedException` → 403.

### 14.2 GlobalExceptionHandler

A single `@RestControllerAdvice` class handles all exceptions. Every handler produces the same JSON envelope:

```
{
  "error": "<ERROR_CODE>",
  "message": "<Human-readable description>",
  "timestamp": "<ISO-8601>",
  "path": "<request URI>"
}
```

The catch-all handler for unrecognised `Exception` types logs the full stack trace server-side and returns a generic 500 message — internal details are never exposed to the client.

Validation failures collect all field-level constraint messages into the `message` field rather than returning just the first failure.

---

## 15. DTO Design

### 15.1 Request DTOs

Request DTOs use Lombok `@Data` (generates getters, setters, equals, hashCode) with Jakarta Bean Validation annotations. Key validation rules:

- Email fields: `@NotBlank @Email`
- Password: `@NotBlank @Size(min = 8, max = 100)`
- Name: `@NotBlank @Size(max = 100)`
- Role: `@NotNull`
- Platforms list: `@NotEmpty`
- JD input wrapper: custom `@ValidJdInput` — exactly one of `jdText` or `jdFile` must be present

### 15.2 Response DTOs

Response DTOs use Java 17 records (immutable, compact constructor, auto-generated accessor methods). Records cannot be mutated after construction, which is correct for response objects.

`PageResponse<T>` is a generic record wrapping a `List<T>` content, `totalElements`, `totalPages`, `page`, and `size`. It has a static factory method accepting a Spring `Page<T>` to simplify conversion in service implementations.

### 15.3 DTO Mapping with MapStruct

`SearchMapper`, `CandidateMapper`, and `ShareRequestMapper` are MapStruct `@Mapper` interfaces with `componentModel = "spring"`. They are injected as Spring beans into service implementations. MapStruct generates the implementation at compile time — no reflection at runtime, and any field mismatch is a compile error, not a silent null.

---

## 16. MongoDB Index Configuration

Indexes are applied in `MongoConfig` via an `@EventListener(ApplicationReadyEvent.class)` method using `MongoTemplate.indexOps()`. Auto-index-creation in `application.yml` is set to `false` to prevent Spring Data from scanning `@Indexed` annotations on every startup, which causes latency in production.

Index summary:

| Collection | Index | Type |
|---|---|---|
| `users` | `{ email: 1 }` | Unique |
| `searches` | `{ userId: 1 }` | Standard |
| `searches` | `{ userId: 1, createdAt: -1 }` | Compound |
| `searches` | `{ sharedWith: 1 }` | Standard (multikey) |
| `share_requests` | `{ ownerUserId: 1, status: 1, requestedAt: -1 }` | Compound |
| `share_requests` | `{ requesterUserId: 1, requestedAt: -1 }` | Compound |
| `share_requests` | `{ searchId: 1, requesterUserId: 1, status: 1 }` | Compound |
| `candidates` | `{ searchId: 1, runId: 1, source: 1, sourceUsername: 1 }` | Unique compound |
| `candidates` | `{ searchId: 1, isActive: 1, matchScore: -1 }` | Compound |
| `sourcing_tasks` | `{ searchId: 1 }` | Standard |
| `sourcing_tasks` | `{ status: 1 }` | Standard |

---

## 17. AI Service Integration — Phase 1 Behaviour

The AI service does not exist in Phase 1. The backend is fully wired to call it via `AiServiceClientImpl` (WebClient). Two approaches are used to develop and test without a live AI service:

**WireMock in integration tests:** `AiServiceClientImpl` is the real implementation used in all integration tests. WireMock stubs the AI service endpoints, validates the HTTP method, path, and request body, and returns a canned response. This tests HTTP serialisation, timeout handling, and error path (e.g. AI service returning 500 → backend returns 503) without a live Python process.

**Stub Spring bean for manual dev/demo:** A `dev-stub` Spring profile provides an alternative `AiServiceClient` bean marked `@Primary` that returns a hardcoded `ParsedJd` without making any HTTP call. This allows the Phase 3 frontend developer to test the full UI flow against a running backend without Phase 2 being ready. The stub profile is activated via `SPRING_PROFILES_ACTIVE=dev-stub` in the local environment only. It is never deployed.

---

## 18. Actuator and Health

Only the `/actuator/health` endpoint is enabled. No metrics, env, or beans endpoints are exposed. Health details are not included in the response (shows only `{"status": "UP"}`). This endpoint is used by Render's platform health-check to determine when the container is ready to serve traffic after a cold start.

---

## 19. Testing Strategy

### 19.1 Unit Tests (Service Layer)

Every service implementation has a corresponding unit test class in `src/test/java/.../service/`. All dependencies (repositories, AI client) are Mockito mocks injected via constructor. Tests cover:

- Every happy path for each public service method
- Every business rule violation (duplicate email, wrong ownership, concurrent sourcing trigger, invalid file type)
- Every cascade (deleteSearch removes candidates and tasks)
- Boundary conditions (empty results, zero candidates found, AI service timeout)

Target: 80%+ line coverage on `service/impl/`.

### 19.2 Integration Tests (Controller Layer)

Every controller has an integration test class suffixed `IT`. The Spring application context loads fully. MongoDB is provided by a Testcontainers `MongoDBContainer`. Kafka is provided by `@EmbeddedKafka`. The AI service is stubbed by WireMock.

Each test class covers:
- Happy path for every endpoint
- Auth validation (missing token, expired token, wrong role)
- Ownership enforcement (user A trying to delete user B's search → 403)
- Validation errors (missing fields, wrong format → 400)
- Not-found cases → 404
- AI service failure → 503
- Sharing flow coverage: create request (201), recruiter incoming list (200), approve/reject (200), duplicate pending request (409), unauthorized approve/reject (403)

### 19.3 Kafka Tests

`SourcingRequestProducer` has a test that publishes a message to an embedded Kafka topic and verifies the message was received by a test consumer with the correct payload structure.

`SourcingResultConsumer` has an integration test that publishes a result message to the embedded Kafka topic and asserts that the SourcingTask and Search documents in the test MongoDB are updated correctly.

### 19.4 Security Tests

`JwtTokenProvider` is unit-tested for: valid token generation and claim extraction, expired token rejection, tampered signature rejection, wrong token type rejection (e.g. using a refresh token as an access token).

### 19.5 Test Naming Convention

```
given_<context>_when_<action>_then_<expectedOutcome>
```

Example: `given_hiringManagerJwt_when_deleteSearch_then_returns403`

---

## 20. Phase 1 Deliverables Checklist

| Deliverable | Description |
|---|---|
| `pom.xml` | All dependencies, Java 17 compiler config, Maven wrapper |
| `application.yml` | Full config for local and prod profiles |
| `docker-compose.yml` | MongoDB + Kafka + backend service |
| Domain models | User, Search, Candidate, SourcingTask, ShareRequest, ParsedJd, ScoreBreakdown |
| Security | JwtTokenProvider, JwtAuthenticationFilter, SecurityConfig, UserDetailsServiceImpl, RateLimitFilter |
| Auth endpoints | Register, login, refresh, me — BCrypt, JWT, validation |
| Search endpoints | Create (file forwarding to AI + text path), list (filtered/paged), get, delete (cascade) |
| Share request endpoints | Request access, list incoming/outgoing, approve, reject |
| Sourcing endpoints | Trigger (run-id generation, Kafka produce), poll status |
| Candidate endpoints | List (filtered/paged by run or all runs), soft delete, export (CSV + JSON streaming) |
| Kafka | SourcingRequestProducer, SourcingResultConsumer, topic beans, message DTOs |
| AI client | AiServiceClientImpl (WebClient, two methods), StubAiServiceClient (dev-stub profile) |
| Exception handling | GlobalExceptionHandler covering all defined error codes and Spring built-ins |
| MongoDB indexes | All indexes applied on startup via MongoConfig |
| Share request data layer | ShareRequest model + repository + indexes + service |
| MapStruct mappers | SearchMapper, CandidateMapper, ShareRequestMapper |
| Unit tests | Service layer — 80%+ line coverage |
| Integration tests | All controller endpoints + Kafka consumer, using Testcontainers + WireMock + EmbeddedKafka |
