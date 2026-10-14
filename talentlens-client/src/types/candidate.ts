import type { Platform } from './search'

export type CandidateSource = Platform

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
  // Short reasons the candidate was picked, e.g. "Top answerer in [go]".
  signals?: string[]
  // They say they are looking (GitHub "hireable", an HN "Who wants to be hired?" post).
  openToWork?: boolean
  matchScore: number
  scoreBreakdown: ScoreBreakdown
  isActive: boolean
  createdAt: string
}

export interface CandidateFilters {
  // Sourcing run to show; unset means the latest completed run.
  runId?: string
  skill?: string
  source?: CandidateSource | 'ALL'
  minScore?: number
  maxScore?: number
  sortBy?: 'matchScore' | 'createdAt'
  sortDir?: 'asc' | 'desc'
  page?: number
  size?: number
}
