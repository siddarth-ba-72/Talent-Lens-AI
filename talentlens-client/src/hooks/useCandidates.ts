import { useQuery } from '@tanstack/react-query'
import { getCandidates } from '@/api/candidateApi'
import type { CandidateFilters } from '@/types/candidate'
import { QUERY_KEYS } from '@/utils/constants'

export function useCandidates(searchId: string, filters: CandidateFilters) {
  return useQuery({
    queryKey: [QUERY_KEYS.CANDIDATES, searchId, filters],
    queryFn: () => getCandidates(searchId, filters),
    staleTime: 30_000,
    enabled: !!searchId,
    placeholderData: (prev) => prev,
  })
}
