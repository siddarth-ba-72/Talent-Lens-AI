import type { Platform } from '@/types/search'

export const POLLING_INTERVAL_MS = 3000
export const SEARCH_PAGE_SIZE = 10
export const CANDIDATE_PAGE_SIZE = 20
export const MAX_FILE_SIZE_BYTES = 4 * 1024 * 1024 // 4 MB: Vercel rejects request bodies over 4.5 MB
export const ALLOWED_FILE_TYPES = ['.txt', '.pdf', '.docx']
export const ALLOWED_MIME_TYPES = [
  'text/plain',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]
export const MIN_JD_LENGTH = 100
export const DEFAULT_PLATFORMS: Platform[] = ['GITHUB', 'STACKOVERFLOW']
export const TOAST_DURATION_MS = 4000

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'tl_access',
  REFRESH_TOKEN: 'tl_refresh',
  THEME: 'tl_theme',
} as const

export const OAUTH_SESSION_KEYS = {
  PKCE_VERIFIER: 'tl_pkce_verifier',
  STATE: 'tl_oauth_state',
  NONCE: 'tl_oidc_nonce',
} as const

export const GOOGLE_OAUTH = {
  AUTHORIZE_URL: 'https://accounts.google.com/o/oauth2/v2/auth',
  SCOPE: 'openid email profile',
  CALLBACK_PATH: '/oauth/google/callback',
} as const

export const QUERY_KEYS = {
  SEARCHES: 'searches',
  SEARCH: 'search',
  CANDIDATES: 'candidates',
  SOURCING_STATUS: 'sourcingStatus',
  SOURCING_RUNS: 'sourcingRuns',
  SHARE_REQUESTS: 'shareRequests',
  RECRUITERS: 'recruiters',
  ME: 'me',
} as const
