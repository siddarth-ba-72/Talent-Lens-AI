import axiosInstance from './axiosInstance'
import type { Candidate, CandidateFilters } from '@/types/candidate'
import type { PageResponse } from '@/types/common'

export async function getCandidates(searchId: string, filters: CandidateFilters): Promise<PageResponse<Candidate>> {
  const params = new URLSearchParams()
  if (filters.skill) params.set('skill', filters.skill)
  if (filters.source && filters.source !== 'ALL') params.set('source', filters.source)
  if (filters.minScore !== undefined) params.set('minScore', String(filters.minScore))
  if (filters.maxScore !== undefined) params.set('maxScore', String(filters.maxScore))
  if (filters.sortBy) params.set('sortBy', filters.sortBy)
  if (filters.sortDir) params.set('sortDir', filters.sortDir ?? 'desc')
  params.set('page', String(filters.page ?? 0))
  params.set('size', String(filters.size ?? 20))

  const res = await axiosInstance.get<PageResponse<Candidate>>(`/searches/${searchId}/candidates`, { params })
  return res.data
}

export async function deleteCandidate(searchId: string, candidateId: string): Promise<void> {
  await axiosInstance.delete(`/searches/${searchId}/candidates/${candidateId}`)
}

export async function exportCandidates(
  searchId: string,
  format: 'csv' | 'json',
  filters?: CandidateFilters
): Promise<Blob> {
  const params = new URLSearchParams({ format })
  if (filters?.skill) params.set('skill', filters.skill)
  if (filters?.source && filters.source !== 'ALL') params.set('source', filters.source)
  if (filters?.minScore !== undefined) params.set('minScore', String(filters.minScore))
  if (filters?.maxScore !== undefined) params.set('maxScore', String(filters.maxScore))

  const res = await axiosInstance.get(`/searches/${searchId}/candidates/export`, {
    params,
    responseType: 'blob',
  })
  return res.data as Blob
}
