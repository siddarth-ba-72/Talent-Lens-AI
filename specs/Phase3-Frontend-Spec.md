# TalentLens — Phase 3: React Frontend Specification

---

## 1. Scope of Phase 3

Phase 3 delivers the complete React frontend in `talentlens-client/`. At the end of this phase the application must be:

- Fully functional against the live Phase 1 backend and Phase 2 AI service
- Covering all user flows for RECRUITER and HIRING_MANAGER roles
- Deployable to Vercel with a single environment variable (`VITE_API_BASE_URL`)
- Runnable locally via `npm run dev` with a proxy to the backend

Phase 3 **includes**: auth, search CRUD, JD parsing flow, candidate sourcing + polling, candidate review, export, and the full share request workflow.

Phase 3 **does not** include: WebSocket push, analytics dashboard, candidate notes, email outreach, or any backend changes.

---

## 2. Technology Stack

| Concern | Library / Version |
|---|---|
| Language | TypeScript 5 |
| Framework | React 18 + Vite 5 |
| Styling | Tailwind CSS v3 |
| Component Library | **shadcn/ui** (Radix UI primitives + Tailwind — components are copied into the repo, no runtime dependency) |
| State Management | **Zustand** (auth state, UI state) |
| Server State | **TanStack Query v5** (searches, candidates, share requests — caching, pagination, background refetch) |
| Routing | React Router v6 |
| HTTP Client | Axios (instance with request/response interceptors) |
| Forms | react-hook-form v7 + zod v3 |
| Theme | Light / Dark mode toggle via Tailwind `dark:` variant + `class` strategy |
| Token Storage | `localStorage` |
| Build | Vite 5 |
| Linting | ESLint + Prettier |

---

## 3. Project Directory Structure

```
talentlens-client/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                         # Axios instance + typed API functions
│   │   ├── axiosInstance.ts         # Base URL, interceptors, token refresh
│   │   ├── authApi.ts               # register, login, refresh, me
│   │   ├── searchApi.ts             # CRUD + source + status
│   │   ├── candidateApi.ts          # list, delete, export
│   │   └── shareRequestApi.ts       # create, incoming, outgoing, approve, reject
│   ├── stores/                      # Zustand slices
│   │   ├── authStore.ts             # user, tokens, login/logout/refresh actions
│   │   └── uiStore.ts               # theme (light/dark), global toast state
│   ├── hooks/                       # TanStack Query hooks
│   │   ├── useSearches.ts           # paginated search list
│   │   ├── useSearch.ts             # single search detail
│   │   ├── useCandidates.ts         # paginated candidates with filters
│   │   ├── useSourcingStatus.ts     # polling hook (3s interval, auto-stop)
│   │   ├── useShareRequests.ts      # incoming + outgoing request lists
│   │   └── useExport.ts             # CSV/JSON download trigger
│   ├── components/
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   └── RegisterForm.tsx
│   │   ├── layout/
│   │   │   ├── Navbar.tsx           # Logo, nav links, role badge, theme toggle, logout
│   │   │   ├── ProtectedRoute.tsx   # Redirect unauthenticated → /login
│   │   │   ├── PublicRoute.tsx      # Redirect authenticated → /dashboard
│   │   │   └── RoleGuard.tsx        # Conditionally render based on role
│   │   ├── search/
│   │   │   ├── SearchCard.tsx       # Title, status badge, candidate count, date
│   │   │   ├── SearchFilters.tsx    # Keyword, status, date range, sort
│   │   │   ├── JdInputForm.tsx      # Textarea + file upload toggle
│   │   │   ├── JdFileUpload.tsx     # Drag-and-drop / browse for .txt, .pdf, .docx
│   │   │   ├── ParsedJdSummary.tsx  # Skills tags, responsibilities, exp level, domain
│   │   │   ├── PlatformSelector.tsx # GitHub / Stack Overflow checkboxes
│   │   │   └── SourcingStatus.tsx   # Animated progress indicator + status text
│   │   ├── candidate/
│   │   │   ├── CandidateCard.tsx    # Profile card with all fields
│   │   │   ├── CandidateFilters.tsx # Skill, source, score range
│   │   │   ├── MatchScoreBadge.tsx  # Colour-coded score chip (green/amber/red)
│   │   │   ├── SkillTags.tsx        # Pill list of skills
│   │   │   └── ExportButton.tsx     # CSV / JSON download split button
│   │   ├── share/
│   │   │   ├── RequestAccessModal.tsx   # HM: pick recruiter + search, add note
│   │   │   ├── IncomingRequestCard.tsx  # Recruiter: approve / reject inline
│   │   │   └── ShareRequestBadge.tsx    # Badge count on dashboard nav
│   │   └── common/
│   │       ├── Pagination.tsx
│   │       ├── SortBar.tsx
│   │       ├── LoadingSpinner.tsx
│   │       ├── ConfirmDialog.tsx        # Reusable destructive-action dialog
│   │       ├── ThemeToggle.tsx          # Sun/moon icon button
│   │       └── Toast.tsx               # Success / error / info toasts
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── NewSearchPage.tsx
│   │   ├── SearchDetailPage.tsx
│   │   └── ShareRequestsPage.tsx        # Recruiter: incoming queue
│   ├── types/
│   │   ├── auth.ts                      # User, LoginRequest, RegisterRequest, TokenResponse
│   │   ├── search.ts                    # Search, ParsedJd, SourcingStatus, CreateSearchRequest
│   │   ├── candidate.ts                 # Candidate, ScoreBreakdown, CandidateFilters
│   │   ├── shareRequest.ts              # ShareRequest, CreateShareRequest
│   │   └── common.ts                    # PageResponse<T>, ApiError
│   ├── utils/
│   │   ├── constants.ts                 # API base URL, polling interval, page sizes
│   │   └── formatters.ts                # date, score, platform label formatters
│   ├── App.tsx                          # Router + QueryClientProvider + theme wrapper
│   └── main.tsx
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── .env.example
├── Dockerfile
└── package.json
```

---

## 4. Zustand Store Design

### 4.1 `authStore.ts`

```ts
interface AuthState {
  user: { id: string; name: string; email: string; role: 'RECRUITER' | 'HIRING_MANAGER' } | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean

  login: (credentials: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  refresh: () => Promise<void>
  logout: () => void
  hydrateFromStorage: () => void   // called once on app mount
}
```

- `login` calls `authApi.login`, stores tokens in Zustand state AND `localStorage` (`tl_access`, `tl_refresh`)
- `refresh` calls `authApi.refresh`, updates `accessToken` in state + `localStorage`
- `logout` clears state + `localStorage` + calls `queryClient.clear()`
- `hydrateFromStorage` runs on `App.tsx` mount — reads from `localStorage`, sets state, calls `/api/auth/me` to revalidate user object

### 4.2 `uiStore.ts`

```ts
interface UiState {
  theme: 'light' | 'dark'
  toasts: Toast[]

  toggleTheme: () => void
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
}
```

- `theme` is persisted to `localStorage` (`tl_theme`) and applied to `<html>` as a class (`dark`)
- `addToast` auto-removes toasts after 4 seconds

---

## 5. Axios Interceptor Design

### `axiosInstance.ts`

```
Request interceptor:
  - Read accessToken from authStore
  - Inject: Authorization: Bearer <token>

Response interceptor (error path):
  - If status === 401 AND request has not been retried:
    - Call authStore.refresh()
    - Retry original request with new accessToken
    - If refresh fails → authStore.logout() → redirect to /login
  - All other errors → reject with ApiError shape
```

No token is ever embedded in source code. The Axios `baseURL` reads from `import.meta.env.VITE_API_BASE_URL`.

---

## 6. TanStack Query Usage

Each hook wraps a specific API call and returns data + loading/error state. Hooks live in `src/hooks/`.

| Hook | Query key | Stale time | Notes |
|---|---|---|---|
| `useSearches(filters)` | `['searches', filters]` | 30s | Paginated; refetch on filter/page change |
| `useSearch(id)` | `['search', id]` | 60s | Single search detail |
| `useCandidates(id, filters)` | `['candidates', id, filters]` | 30s | Paginated with sort + filter params |
| `useSourcingStatus(id)` | `['sourcingStatus', id]` | 0 (always fresh) | Polled every 3s; disabled when status is COMPLETED or FAILED |
| `useShareRequests(type)` | `['shareRequests', type]` | 30s | `type`: 'incoming' | 'outgoing' |

Mutations use `useMutation` from TanStack Query. On success they call `queryClient.invalidateQueries` to bust relevant caches.

---

## 7. Routing

```tsx
<Routes>
  {/* Public */}
  <Route element={<PublicRoute />}>
    <Route path="/login"    element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
  </Route>

  {/* Protected — any role */}
  <Route element={<ProtectedRoute />}>
    <Route path="/dashboard"         element={<DashboardPage />} />
    <Route path="/searches/:id"      element={<SearchDetailPage />} />
    <Route path="/share-requests"    element={<ShareRequestsPage />} />   {/* RECRUITER only */}
  </Route>

  {/* Protected — RECRUITER only */}
  <Route element={<ProtectedRoute requiredRole="RECRUITER" />}>
    <Route path="/searches/new" element={<NewSearchPage />} />
  </Route>

  <Route path="*" element={<Navigate to="/dashboard" replace />} />
</Routes>
```

`ProtectedRoute` with `requiredRole` renders a 403 page (or redirects to `/dashboard`) for the wrong role.

---

## 8. Page Specifications

### 8.1 LoginPage `/login`

- Email + password form (react-hook-form + zod)
- "Remember me" checkbox (keeps refresh token in localStorage vs. sessionStorage)
- On success → redirect to `/dashboard`
- On error → inline error message below the form
- Link to `/register`

### 8.2 RegisterPage `/register`

- Name, email, password, confirm password, role (select: Recruiter / Hiring Manager)
- Zod validation: email format, password min 8 chars, passwords must match
- On success → redirect to `/login` with a success toast
- Link to `/login`

### 8.3 DashboardPage `/dashboard`

**RECRUITER view:**
- Header: "My Searches" + "New Search" button
- Filter bar: keyword text input, status multi-select (PENDING / SOURCING / COMPLETED / FAILED), date range
- Sort: Date Created (default desc) / Candidate Count / Title
- Search card list with pagination (10 per page)
- Incoming share request badge in Navbar → links to `/share-requests`
- Empty state: prompt to create first search

**HIRING_MANAGER view:**
- Header: "Shared Searches"
- Filter bar: keyword search only
- Search cards for searches shared with them
- "Request Access" button on each card they don't have access to → opens `RequestAccessModal`
- Empty state: prompt to request access from a recruiter

### 8.4 NewSearchPage `/searches/new` (RECRUITER only)

**Step 1 — JD Input:**
- Toggle: "Paste Text" / "Upload File"
- Paste: large textarea with character counter
- Upload: drag-and-drop zone accepting `.txt`, `.pdf`, `.docx` (max 5MB); shows filename + size on selection
- "Analyse JD" button → calls `POST /api/searches` → shows loading state
- On success → renders ParsedJdSummary below, preserves input

**Step 2 — ParsedJdSummary (appears inline after analysis):**
- Search title (editable inline)
- Skills: pill tags
- Experience level badge
- Domain badge
- Responsibilities: bulleted list (collapsible)
- Qualifications: bulleted list (collapsible)
- "Edit JD" link re-shows input and resets summary

**Step 3 — Source Candidates:**
- Platform checkboxes: GitHub (default checked), Stack Overflow (default checked)
- "Source Candidates" button → calls `POST /api/searches/:id/source` → redirects to SearchDetailPage with sourcing in progress

### 8.5 SearchDetailPage `/searches/:id`

**Layout:**
- Left panel (collapsible): Parsed JD summary — same as ParsedJdSummary component
- Right/main area: Candidates section

**Actions bar (RECRUITER only):**
- "Re-search Candidates" button → `POST /api/searches/:id/source` → restarts polling
- "Delete Search" button → ConfirmDialog → `DELETE /api/searches/:id` → redirect to `/dashboard`
- `SourcingStatus` component (shown when sourcing is active or last run failed)

**Candidates section:**
- Filter bar: skill text input (comma-separated), source select (ALL / GITHUB / STACKOVERFLOW), score range slider (0–100), sort (Match Score desc default / asc / date added)
- Candidate cards (20 per page, paginated)
- Export button: split button CSV / JSON
- Empty state: "No candidates yet — trigger sourcing to find candidates"
- "No results" state when filters return nothing

**CandidateCard:**
- Avatar (initials fallback), Name + profile URL (external link), Source badge
- MatchScoreBadge: ≥70 green, 40-69 amber, <40 red
- Score breakdown tooltip: skill match %, experience match %
- Skills: SkillTags component (max 8 visible, "+N more" expander)
- Experience: role list (truncated)
- Education
- Contact info (if available)
- "Remove Candidate" button (RECRUITER only) → soft delete

### 8.6 ShareRequestsPage `/share-requests` (RECRUITER only)

- Tab toggle: Incoming / Outgoing (future HIRING_MANAGER use)
- Incoming: list of IncomingRequestCard components
  - Requester name, search title, note, requested date
  - Approve / Reject inline buttons with confirmation
- Badge count in Navbar updates after approve/reject
- Empty state for no pending requests

---

## 9. Theme (Light / Dark Mode)

Tailwind is configured with `darkMode: 'class'`. The `toggleTheme` action in `uiStore` toggles `dark` class on `<html>`. shadcn/ui components respect the `dark:` variants automatically.

Default theme: system preference detected on first load via `window.matchMedia('(prefers-color-scheme: dark)')`.

Persisted to `localStorage` (`tl_theme`) across sessions.

---

## 10. Form Validation (Zod Schemas)

| Form | Validation |
|---|---|
| Login | email required + valid format, password required |
| Register | name min 2 chars, email valid, password min 8 chars, passwords match, role required |
| JD Text Input | min 100 chars |
| File Upload | type in [pdf, docx, txt], max 5MB |
| Source Candidates | at least 1 platform selected |
| Share Request | searchId required, recruiterUserId required, note max 300 chars |

---

## 11. Error Handling

| Scenario | Handling |
|---|---|
| 401 (expired token) | Axios interceptor auto-refreshes and retries once |
| 401 (refresh also fails) | Logout + redirect to `/login` + toast "Session expired" |
| 403 (wrong role) | Toast "You don't have permission" + redirect to `/dashboard` |
| 404 | Toast "Not found" |
| 422 / 400 (validation) | Field-level errors from backend mapped to react-hook-form |
| 500 / network error | Toast "Something went wrong. Please try again." |
| Sourcing task FAILED | `SourcingStatus` renders failure message with "Retry" button |

---

## 12. Polling Design (`useSourcingStatus`)

```ts
useSourcingStatus(searchId: string, taskId: string | null) => {
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | null
  completedAt: string | null
}
```

- Calls `GET /api/searches/:id/source-status` every 3 seconds
- `refetchInterval` is set to `3000` while status is `PENDING` or `IN_PROGRESS`
- `refetchInterval` is `false` once status is `COMPLETED` or `FAILED`
- On `COMPLETED` → invalidates `['candidates', searchId]` to reload candidate list
- Handles the case where no sourcing task exists (taskId is null) gracefully

---

## 13. Export Flow (`useExport`)

```ts
useExport(searchId: string) => {
  exportCsv: (filters?) => void
  exportJson: (filters?) => void
  isExporting: boolean
}
```

- Calls `GET /api/searches/:id/candidates/export?format=csv|json` with current filter params
- Response is a `Blob` — the hook creates an object URL and triggers `<a download>` click
- Cleans up the object URL after the download starts
- Shows loading state on the ExportButton during the request

---

## 14. Vite Dev Proxy

`vite.config.ts` proxies `/api` to avoid CORS during local development:

```ts
server: {
  proxy: {
    '/api': {
      target: env.VITE_API_BASE_URL || 'http://localhost:8080',
      changeOrigin: true,
    }
  }
}
```

---

## 15. Dockerfile (Multi-Stage)

```dockerfile
# --- Build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# --- Serve stage ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

`nginx.conf` must include `try_files $uri /index.html` for client-side routing to work.

---

## 16. Environment Variables

```bash
# .env.example
VITE_API_BASE_URL=http://localhost:8080
```

Only one variable required. All other config (API routes, timeouts, page sizes) lives in `src/utils/constants.ts`.

---

## 17. Implementation Phases (within Phase 3)

| Sub-phase | Scope |
|---|---|
| 3.1 | Project scaffold: Vite + Tailwind + shadcn/ui setup, Zustand stores, Axios instance, routing skeleton |
| 3.2 | Auth: Login, Register pages, token storage, interceptors, ProtectedRoute |
| 3.3 | Dashboard: search list, filters, pagination (RECRUITER view) |
| 3.4 | NewSearchPage: JD input, file upload, parsed JD summary, platform selection, source trigger |
| 3.5 | SearchDetailPage: candidate list, filters, pagination, sourcing status polling |
| 3.6 | Candidate detail: score breakdown, skills, export (CSV + JSON) |
| 3.7 | Share request workflow: HM request access modal, recruiter incoming queue, approve/reject |
| 3.8 | HIRING_MANAGER dashboard view, shared searches, role-gating |
| 3.9 | Dark mode, polish, error states, empty states, responsive layout |
| 3.10 | Dockerfile, Vercel config, .env.example, smoke test against live backend |

---

## 18. Non-Functional Requirements

| Concern | Target |
|---|---|
| Initial page load | < 2s (Vite tree-shaking + code splitting by route) |
| Lighthouse accessibility | ≥ 85 (semantic HTML, aria labels on interactive elements) |
| Responsive breakpoints | sm (mobile), md (tablet), lg (desktop) |
| Browser support | Chrome, Firefox, Safari, Edge (latest) |
| TypeScript strictness | `strict: true` in tsconfig — no `any` except in Axios error handling |
