import { useQuery } from '@tanstack/react-query'
import { getPlatformAvailability } from '@/api/searchApi'
import type { Platform } from '@/types/search'
import { QUERY_KEYS } from '@/utils/constants'

// Which platforms the server can source from (a recruiter-only endpoint, hence `enabled`).
// Until it answers, every platform counts as available.
export function usePlatforms(enabled = true) {
  const query = useQuery({
    queryKey: [QUERY_KEYS.PLATFORMS],
    queryFn: getPlatformAvailability,
    staleTime: 5 * 60_000,
    enabled,
  })
  const unavailable = new Set(query.data?.filter((p) => !p.available).map((p) => p.platform))
  return { ...query, isAvailable: (platform: Platform) => !unavailable.has(platform) }
}
