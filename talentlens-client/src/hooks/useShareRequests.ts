import { useQuery } from '@tanstack/react-query'
import { getIncomingRequests, getOutgoingRequests } from '@/api/shareRequestApi'
import { QUERY_KEYS } from '@/utils/constants'

export function useShareRequests(type: 'incoming' | 'outgoing', enabled = true) {
  return useQuery({
    queryKey: [QUERY_KEYS.SHARE_REQUESTS, type],
    queryFn: () => (type === 'incoming' ? getIncomingRequests() : getOutgoingRequests()),
    staleTime: 30_000,
    enabled,
  })
}
