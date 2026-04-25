export const POLLING_INTERVAL_MS = 3000
export const SEARCH_PAGE_SIZE = 10
export const CANDIDATE_PAGE_SIZE = 20
export const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024 // 5 MB
export const ALLOWED_FILE_TYPES = ['.txt', '.pdf', '.docx']
export const ALLOWED_MIME_TYPES = [
  'text/plain',
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]
export const MIN_JD_LENGTH = 100
export const TOAST_DURATION_MS = 4000

export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'tl_access',
  REFRESH_TOKEN: 'tl_refresh',
  THEME: 'tl_theme',
} as const

export const QUERY_KEYS = {
  SEARCHES: 'searches',
  SEARCH: 'search',
  CANDIDATES: 'candidates',
  SOURCING_STATUS: 'sourcingStatus',
  SHARE_REQUESTS: 'shareRequests',
  RECRUITERS: 'recruiters',
  ME: 'me',
} as const
