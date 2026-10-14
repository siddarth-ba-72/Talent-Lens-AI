export type SearchStatus = 'PENDING' | 'SOURCING' | 'COMPLETED' | 'FAILED'
export type SourcingTaskStatus = 'IDLE' | 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'
export type Platform = 'GITHUB' | 'STACKOVERFLOW'

export interface ParsedJd {
  skills: string[]
  experienceLevel: string
  responsibilities: string[]
  qualifications: string[]
  technologies: string[]
  domain: string
  summary: string
}

export interface Search {
  id: string
  title: string
  status: SearchStatus
  rawJdText: string
  parsedJd: ParsedJd | null
  candidateCount: number
  platforms: Platform[]
  sharedWith: string[]
  createdAt: string
  updatedAt: string
}

export interface CreateSearchRequest {
  jdText?: string
  jdFile?: File
}

export interface SourcingRequest {
  platforms: Platform[]
}

// One sourcing run of a search (the API calls it a task). Each run keeps its own candidates.
export interface SourcingStatusResponse {
  taskId: string
  searchId: string
  runId: string
  status: SourcingTaskStatus
  candidatesFound: number
  error: string | null
  startedAt: string
  completedAt: string | null
}

export interface SearchFilters {
  keyword?: string
  status?: SearchStatus[]
  dateFrom?: string
  dateTo?: string
  sortBy?: 'createdAt' | 'candidateCount' | 'title'
  sortDir?: 'asc' | 'desc'
  page?: number
  size?: number
}
