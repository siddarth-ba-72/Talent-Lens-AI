import { useQuery } from '@tanstack/react-query'
import { getSearches } from '@/api/searchApi'
import type { SearchFilters } from '@/types/search'
import { QUERY_KEYS } from '@/utils/constants'

export function useSearches(filters: SearchFilters) {
  return useQuery({
    queryKey: [QUERY_KEYS.SEARCHES, filters],
    queryFn: () => getSearches(filters),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  })
}
