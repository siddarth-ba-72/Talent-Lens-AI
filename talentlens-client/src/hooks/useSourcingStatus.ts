import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getSourcingStatus } from '@/api/searchApi'
import type { SourcingStatusResponse, SourcingTaskStatus } from '@/types/search'
import { POLLING_INTERVAL_MS, QUERY_KEYS } from '@/utils/constants'

function isRunning(status?: SourcingTaskStatus) {
  return status === 'PENDING' || status === 'IN_PROGRESS'
}

export function useSourcingStatus(searchId: string, enabled: boolean) {
  const queryClient = useQueryClient()

  return useQuery({
    queryKey: [QUERY_KEYS.SOURCING_STATUS, searchId],
    queryFn: async () => {
      const previous = queryClient.getQueryData<SourcingStatusResponse>([QUERY_KEYS.SOURCING_STATUS, searchId])
      const result = await getSourcingStatus(searchId)
      // A run finished since the last poll (a different task means one started and finished in between).
      const finished =
        previous && !isRunning(result.status) && (isRunning(previous.status) || previous.taskId !== result.taskId)
      if (finished) {
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.CANDIDATES, searchId] })
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SOURCING_RUNS, searchId] })
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SEARCH, searchId] })
        queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SEARCHES] })
      }
      return result
    },
    enabled: enabled && !!searchId,
    staleTime: 0,
    // Poll only while a run is under way. A search that was never sourced answers 404 and is not polled.
    refetchInterval: (query) => (isRunning(query.state.data?.status) ? POLLING_INTERVAL_MS : false),
  })
}
