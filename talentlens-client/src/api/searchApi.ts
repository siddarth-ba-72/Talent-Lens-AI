import axiosInstance from './axiosInstance'
import type {
  Platform,
  PlatformAvailability,
  Search,
  SearchFilters,
  SearchStatus,
  SourcingRequest,
  SourcingStatusResponse,
} from '@/types/search'
import type { PageResponse } from '@/types/common'

// The API names a search's sourcing state differently from the UI's Search model.
type ApiSourcingStatus = 'IDLE' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'

interface ApiSearch extends Omit<Search, 'status' | 'platforms'> {
  sourcingStatus: ApiSourcingStatus
  sourcingPlatforms: Platform[] | null
}

const STATUS_FROM_API: Record<ApiSourcingStatus, SearchStatus> = {
  IDLE: 'PENDING',
  IN_PROGRESS: 'SOURCING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
}

const STATUS_TO_API: Record<SearchStatus, ApiSourcingStatus> = {
  PENDING: 'IDLE',
  SOURCING: 'IN_PROGRESS',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
}

function toSearch({ sourcingStatus, sourcingPlatforms, ...rest }: ApiSearch): Search {
  return { ...rest, status: STATUS_FROM_API[sourcingStatus], platforms: sourcingPlatforms ?? [] }
}

export async function getSearches(filters: SearchFilters): Promise<PageResponse<Search>> {
  const params = new URLSearchParams()
  if (filters.keyword) params.set('keyword', filters.keyword)
  if (filters.status?.length) filters.status.forEach((s) => params.append('status', STATUS_TO_API[s]))
  if (filters.dateFrom) params.set('dateFrom', filters.dateFrom)
  if (filters.dateTo) params.set('dateTo', filters.dateTo)
  if (filters.sortBy) params.set('sortBy', filters.sortBy)
  if (filters.sortDir) params.set('sortDir', filters.sortDir)
  params.set('page', String(filters.page ?? 0))
  params.set('size', String(filters.size ?? 10))

  const res = await axiosInstance.get<PageResponse<ApiSearch>>('/searches', { params })
  return { ...res.data, content: res.data.content.map(toSearch) }
}

export async function getSearch(id: string): Promise<Search> {
  const res = await axiosInstance.get<ApiSearch>(`/searches/${id}`)
  return toSearch(res.data)
}

export async function createSearch(data: FormData): Promise<Search> {
  const jdText = data.get('jdText')
  if (jdText !== null) {
    // Text mode → JSON endpoint
    const res = await axiosInstance.post<ApiSearch>('/searches/jd-text', { jdText })
    return toSearch(res.data)
  } else {
    // File mode → multipart endpoint
    const res = await axiosInstance.post<ApiSearch>('/searches/jd-file', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return toSearch(res.data)
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

// Newest first.
export async function getSourcingRuns(id: string): Promise<SourcingStatusResponse[]> {
  const res = await axiosInstance.get<SourcingStatusResponse[]>(`/searches/${id}/runs`)
  return res.data
}

// Every sourcing platform, and whether the server is configured to use it.
export async function getPlatformAvailability(): Promise<PlatformAvailability[]> {
  const res = await axiosInstance.get<PlatformAvailability[]>('/sourcing/platforms')
  return res.data
}
