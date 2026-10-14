import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Plus, Radar, Search, Share2, BarChart3 } from 'lucide-react'
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
  const firstName = user?.name?.split(' ')[0]

  return (
    <div className="container mx-auto space-y-6 px-4 py-10 sm:px-8">
      {/* Page header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          {firstName && <p className="mb-1 text-sm font-medium text-primary">Welcome back, {firstName}</p>}
          <h1 className="flex items-center gap-3 text-3xl font-semibold">
            {isRecruiter ? 'My searches' : 'Shared searches'}
            {!!data?.totalElements && (
              <span className="rounded-full border bg-card px-2.5 py-0.5 text-sm font-medium text-muted-foreground">
                {data.totalElements}
              </span>
            )}
          </h1>
          <p className="mt-1 text-muted-foreground">
            {isRecruiter
              ? 'Manage your candidate sourcing jobs'
              : 'Searches shared with you by recruiters'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <RoleGuard role="RECRUITER">
            <Button asChild className="shadow-lg shadow-primary/20">
              <Link to="/searches/new">
                <Plus className="h-4 w-4" />
                New search
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
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-16 text-center">
        <Search className="mb-4 h-10 w-10 text-muted-foreground/50" />
        <h3 className="mb-1 text-lg font-semibold">No results found</h3>
        <p className="text-sm text-muted-foreground">Try adjusting your search or clearing the filters.</p>
      </div>
    )
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-dashed bg-card/50 px-6 py-16 text-center">
      <div className="pointer-events-none absolute inset-0 bg-dot-grid opacity-60" aria-hidden="true" />
      <div className="relative">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-solid text-white shadow-lg shadow-primary/25">
          <Search className="h-7 w-7" />
        </div>
        <h3 className="mb-2 text-xl font-semibold">
          {isRecruiter ? 'Start your first search' : 'No shared searches yet'}
        </h3>
        <p className="mx-auto mb-8 max-w-sm text-sm text-muted-foreground">
          {isRecruiter
            ? 'Upload a job description and TalentLens will find and rank matching candidates from GitHub and Stack Overflow.'
            : 'A recruiter needs to share a search with you before it appears here. You can ask one for access.'}
        </p>

        {isRecruiter ? (
          <>
            <div className="mx-auto mb-8 grid max-w-lg gap-3 text-left sm:grid-cols-3">
              {[
                { icon: FileText, label: 'Paste or upload a JD' },
                { icon: Radar, label: 'Source on GitHub and Stack Overflow' },
                { icon: BarChart3, label: 'Review ranked candidates' },
              ].map(({ icon: Icon, label }, i) => (
                <div key={label} className="flex items-center gap-2.5 rounded-xl border bg-background/80 px-3 py-2.5 text-xs font-medium">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <span><span className="text-muted-foreground">{i + 1}.</span> {label}</span>
                </div>
              ))}
            </div>
            <Button asChild className="shadow-lg shadow-primary/20">
              <Link to="/searches/new">
                <Plus className="h-4 w-4" />
                New search
              </Link>
            </Button>
          </>
        ) : (
          <Button asChild variant="outline">
            <Link to="/share-requests">
              <Share2 className="h-4 w-4" />
              Request access
            </Link>
          </Button>
        )}
      </div>
    </div>
  )
}
