import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getSourcingStatus } from '@/api/searchApi'
import { POLLING_INTERVAL_MS, QUERY_KEYS } from '@/utils/constants'

export function useSourcingStatus(searchId: string, enabled: boolean) {
  const queryClient = useQueryClient()

  return useQuery({
    queryKey: [QUERY_KEYS.SOURCING_STATUS, searchId],
    queryFn: async () => {
      const result = await getSourcingStatus(searchId)
      if (result.status === 'COMPLETED') {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.CANDIDATES, searchId] })
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SEARCH, searchId] })
      }
      return result
    },
    enabled: enabled && !!searchId,
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'COMPLETED' || status === 'FAILED') return false
      return POLLING_INTERVAL_MS
    },
  })
}
