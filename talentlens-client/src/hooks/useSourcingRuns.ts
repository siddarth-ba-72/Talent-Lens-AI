import { useQuery } from '@tanstack/react-query'
import { getSourcingRuns } from '@/api/searchApi'
import { QUERY_KEYS } from '@/utils/constants'

export function useSourcingRuns(searchId: string) {
  return useQuery({
    queryKey: [QUERY_KEYS.SOURCING_RUNS, searchId],
    queryFn: () => getSourcingRuns(searchId),
    staleTime: 30_000,
    enabled: !!searchId,
  })
}
