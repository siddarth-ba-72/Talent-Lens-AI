import axiosInstance from './axiosInstance'
import type { ShareRequest, CreateShareRequest } from '@/types/shareRequest'
import type { User } from '@/types/auth'
import type { PageResponse } from '@/types/common'

export async function getRecruiters(): Promise<User[]> {
  const res = await axiosInstance.get<PageResponse<User>>('/share-requests/recruiters')
  return res.data.content ?? []
}

export async function getRecruiterSearches(recruiterId: string): Promise<{ id: string; title: string }[]> {
  const res = await axiosInstance.get<PageResponse<{ id: string; title: string }>>(`/share-requests/recruiters/${recruiterId}/searches`)
  return res.data.content ?? []
}

export async function createShareRequest(data: CreateShareRequest): Promise<ShareRequest> {
  const res = await axiosInstance.post<ShareRequest>('/share-requests', data)
  return res.data
}

export async function getIncomingRequests(): Promise<PageResponse<ShareRequest>> {
  const res = await axiosInstance.get<PageResponse<ShareRequest>>('/share-requests/incoming')
  return res.data
}

export async function getOutgoingRequests(): Promise<PageResponse<ShareRequest>> {
  const res = await axiosInstance.get<PageResponse<ShareRequest>>('/share-requests/outgoing')
  return res.data
}

export async function approveShareRequest(id: string): Promise<ShareRequest> {
  const res = await axiosInstance.post<ShareRequest>(`/share-requests/${id}/approve`)
  return res.data
}

export async function rejectShareRequest(id: string): Promise<ShareRequest> {
  const res = await axiosInstance.post<ShareRequest>(`/share-requests/${id}/reject`)
  return res.data
}
