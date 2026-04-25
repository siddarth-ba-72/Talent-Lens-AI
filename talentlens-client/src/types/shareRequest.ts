export type ShareRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED'

export interface ShareRequest {
  id: string
  searchId: string
  searchTitle?: string | null
  requesterUserId: string
  requesterName?: string | null
  ownerUserId: string
  ownerName?: string | null
  status: ShareRequestStatus
  note: string | null
  requestedAt: string
  resolvedAt: string | null
}

export interface CreateShareRequest {
  searchId: string
  recruiterUserId: string
  note?: string
}
