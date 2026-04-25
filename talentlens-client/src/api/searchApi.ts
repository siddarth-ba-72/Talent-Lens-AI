import axiosInstance from './axiosInstance'
import type { Search, SearchFilters, SourcingRequest, SourcingStatusResponse } from '@/types/search'
import type { PageResponse } from '@/types/common'

export async function getSearches(filters: SearchFilters): Promise<PageResponse<Search>> {
  const params = new URLSearchParams()
  if (filters.keyword) params.set('keyword', filters.keyword)
  if (filters.status?.length) filters.status.forEach((s) => params.append('status', s))
  if (filters.dateFrom) params.set('dateFrom', filters.dateFrom)
  if (filters.dateTo) params.set('dateTo', filters.dateTo)
  if (filters.sortBy) params.set('sortBy', filters.sortBy)
  if (filters.sortDir) params.set('sortDir', filters.sortDir)
  params.set('page', String(filters.page ?? 0))
  params.set('size', String(filters.size ?? 10))

  const res = await axiosInstance.get<PageResponse<Search>>('/searches', { params })
  return res.data
}

export async function getSearch(id: string): Promise<Search> {
  const res = await axiosInstance.get<Search>(`/searches/${id}`)
  return res.data
}

export async function createSearch(data: FormData): Promise<Search> {
  const jdText = data.get('jdText')
  if (jdText !== null) {
    // Text mode → JSON endpoint
    const res = await axiosInstance.post<Search>('/searches/jd-text', { jdText })
    return res.data
  } else {
    // File mode → multipart endpoint
    const res = await axiosInstance.post<Search>('/searches/jd-file', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  }
}

export async function deleteSearch(id: string): Promise<void> {
  await axiosInstance.delete(`/searches/${id}`)
}

export async function triggerSourcing(id: string, data: SourcingRequest): Promise<SourcingStatusResponse> {
  const res = await axiosInstance.post<SourcingStatusResponse>(`/searches/${id}/source`, data)
  return res.data
}

export async function getSourcingStatus(id: string): Promise<SourcingStatusResponse> {
  const res = await axiosInstance.get<SourcingStatusResponse>(`/searches/${id}/source-status`)
  return res.data
}
