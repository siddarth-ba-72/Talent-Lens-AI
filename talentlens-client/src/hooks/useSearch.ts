import { useQuery } from '@tanstack/react-query'
import { getSearch } from '@/api/searchApi'
import { QUERY_KEYS } from '@/utils/constants'

export function useSearch(id: string) {
  return useQuery({
    queryKey: [QUERY_KEYS.SEARCH, id],
    queryFn: () => getSearch(id),
    staleTime: 60_000,
    enabled: !!id,
  })
}
