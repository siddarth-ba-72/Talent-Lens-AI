import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, Share2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { SearchCard, SearchCardSkeleton } from '@/components/search/SearchCard'
import { SearchFiltersBar } from '@/components/search/SearchFilters'
import { Pagination } from '@/components/common/Pagination'
import { RoleGuard } from '@/components/layout/RoleGuard'
import { useSearches } from '@/hooks/useSearches'
import { useAuthStore } from '@/stores/authStore'
import type { SearchFilters } from '@/types/search'
import { SEARCH_PAGE_SIZE } from '@/utils/constants'

const DEFAULT_FILTERS: SearchFilters = {
  sortBy: 'createdAt',
  sortDir: 'desc',
  page: 0,
  size: SEARCH_PAGE_SIZE,
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [filters, setFilters] = useState<SearchFilters>(DEFAULT_FILTERS)

  const { data, isLoading, isFetching } = useSearches(filters)

  const handleFilterChange = (changes: Partial<SearchFilters>) => {
    setFilters((prev) => ({ ...prev, ...changes }))
  }

  const handleReset = () => setFilters(DEFAULT_FILTERS)

  const isRecruiter = user?.role === 'RECRUITER'

  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {isRecruiter ? 'My Searches' : 'Shared Searches'}
          </h1>
          <p className="text-muted-foreground">
            {isRecruiter
              ? 'Manage your candidate sourcing jobs'
              : 'Searches shared with you by recruiters'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <RoleGuard role="RECRUITER">
            <Button asChild>
              <Link to="/searches/new">
                <Plus className="h-4 w-4" />
                New Search
              </Link>
            </Button>
          </RoleGuard>
          <RoleGuard role="HIRING_MANAGER">
            <Button asChild variant="outline">
              <Link to="/share-requests">
                <Share2 className="h-4 w-4" />
                My Requests
              </Link>
            </Button>
          </RoleGuard>
        </div>
      </div>

      {/* Filters */}
      <SearchFiltersBar
        filters={filters}
        onChange={handleFilterChange}
        onReset={handleReset}
        showStatusFilter={isRecruiter}
      />

      {/* Results */}
      <div className="relative">
        {isFetching && !isLoading && (
          <div className="absolute right-0 top-0 text-xs text-muted-foreground flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
            Updating…
          </div>
        )}

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
            {Array.from({ length: 6 }).map((_, i) => <SearchCardSkeleton key={i} />)}
          </div>
        ) : !data?.content?.length ? (
          <EmptyState isRecruiter={isRecruiter} hasFilters={!!(filters.keyword || filters.status?.length)} />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
              {data.content.map((search) => (
                <SearchCard key={search.id} search={search} />
              ))}
            </div>
            {data.totalPages > 1 && (
              <div className="mt-6">
                <Pagination
                  page={filters.page ?? 0}
                  totalPages={data.totalPages}
                  totalElements={data.totalElements}
                  pageSize={filters.size ?? SEARCH_PAGE_SIZE}
                  onPageChange={(page) => handleFilterChange({ page })}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function EmptyState({ isRecruiter, hasFilters }: { isRecruiter: boolean; hasFilters: boolean }) {
  if (hasFilters) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
        <Search className="h-10 w-10 text-muted-foreground/50 mb-4" />
        <h3 className="font-semibold text-lg mb-1">No results found</h3>
        <p className="text-muted-foreground text-sm">Try adjusting your search or clearing the filters.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-16 text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <Search className="h-8 w-8 text-primary" />
      </div>
      <h3 className="font-semibold text-xl mb-2">
        {isRecruiter ? 'Start your first search' : 'No shared searches yet'}
      </h3>
      <p className="text-muted-foreground text-sm mb-6 max-w-sm">
        {isRecruiter
          ? 'Upload a job description and TalentLens will find and rank the best candidates from GitHub and Stack Overflow.'
          : 'A recruiter needs to share a search with you before it appears here.'}
      </p>
      {isRecruiter && (
        <Button asChild>
          <Link to="/searches/new">
            <Plus className="h-4 w-4" />
            New Search
          </Link>
        </Button>
      )}
    </div>
  )
}
