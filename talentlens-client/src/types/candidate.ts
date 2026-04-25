export type CandidateSource = 'GITHUB' | 'STACKOVERFLOW'

export interface ScoreBreakdown {
  skillMatch: number
  experienceMatch: number
  overallFit: number
}

export interface Experience {
  title: string
  company: string
  duration: string
}

export interface Education {
  degree: string
  institution: string
}

export interface Candidate {
  id: string
  searchId: string
  name: string
  source: CandidateSource
  sourceUsername: string
  profileUrl: string
  avatarUrl?: string
  email?: string
  location?: string
  skills: string[]
  experience: Experience[]
  education: Education[]
  matchScore: number
  scoreBreakdown: ScoreBreakdown
  isActive: boolean
  createdAt: string
}

export interface CandidateFilters {
  skill?: string
  source?: CandidateSource | 'ALL'
  minScore?: number
  maxScore?: number
  sortBy?: 'matchScore' | 'createdAt'
  sortDir?: 'asc' | 'desc'
  page?: number
  size?: number
}
