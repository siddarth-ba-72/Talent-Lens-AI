import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Trash2, ChevronDown, Search, RefreshCw, Share2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { ParsedJdSummary } from '@/components/search/ParsedJdSummary'
import { SourcingStatus } from '@/components/search/SourcingStatus'
import { CandidateCard } from '@/components/candidate/CandidateCard'
import { CandidateFiltersBar } from '@/components/candidate/CandidateFilters'
import { ExportButton } from '@/components/candidate/ExportButton'
import { Pagination } from '@/components/common/Pagination'
import { Skeleton } from '@/components/ui/skeleton'
import { RoleGuard } from '@/components/layout/RoleGuard'
import { useSearch } from '@/hooks/useSearch'
import { useCandidates } from '@/hooks/useCandidates'
import { useSourcingStatus } from '@/hooks/useSourcingStatus'
import { deleteSearch, triggerSourcing } from '@/api/searchApi'
import { useUiStore } from '@/stores/uiStore'
import { QUERY_KEYS, CANDIDATE_PAGE_SIZE } from '@/utils/constants'
import { pluralize } from '@/utils/formatters'
import type { CandidateFilters } from '@/types/candidate'
import { cn } from '@/lib/utils'

const DEFAULT_FILTERS: CandidateFilters = {
  sortBy: 'matchScore',
  sortDir: 'desc',
  page: 0,
  size: CANDIDATE_PAGE_SIZE,
}

export default function SearchDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { addToast } = useUiStore()

  const [jdCollapsed, setJdCollapsed] = useState(true)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [candidateFilters, setCandidateFilters] = useState<CandidateFilters>(DEFAULT_FILTERS)

  const { data: search, isLoading: searchLoading } = useSearch(id!)
  const { data: sourcingStatus } = useSourcingStatus(id!, true)
  const { data: candidatesPage, isLoading: candidatesLoading } = useCandidates(id!, candidateFilters)

  const deleteMutation = useMutation({
    mutationFn: () => deleteSearch(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SEARCHES] })
      addToast({ type: 'success', title: 'Search deleted' })
      navigate('/dashboard')
    },
    onError: () => addToast({ type: 'error', title: 'Failed to delete search' }),
  })

  const retryMutation = useMutation({
    mutationFn: () => triggerSourcing(id!, { platforms: search?.platforms ?? [] }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SOURCING_STATUS, id] })
      addToast({ type: 'success', title: 'Sourcing restarted' })
    },
    onError: () => addToast({ type: 'error', title: 'Failed to restart sourcing' }),
  })

  const handleFilterChange = (changes: Partial<CandidateFilters>) => {
    setCandidateFilters((prev) => ({ ...prev, ...changes }))
  }

  if (searchLoading) return <SearchDetailSkeleton />

  if (!search) {
    return (
      <div className="container mx-auto py-16 text-center">
        <p className="text-muted-foreground">Search not found.</p>
        <Button asChild variant="link" className="mt-4">
          <Link to="/dashboard">Back to Dashboard</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/dashboard')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight truncate">{search.title}</h1>
          </div>
          {search.parsedJd?.domain && (
            <p className="text-muted-foreground">{search.parsedJd.domain}</p>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <RoleGuard role="RECRUITER">
            <Button variant="outline" size="sm" asChild>
              <Link to="/share-requests">
                <Share2 className="h-4 w-4" /> Share
              </Link>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-destructive hover:bg-destructive/10"
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </RoleGuard>
        </div>
      </div>

      {/* Sourcing status */}
      {sourcingStatus && sourcingStatus.status !== 'COMPLETED' && sourcingStatus.status !== 'IDLE' && (
        <SourcingStatus
          status={sourcingStatus.status}
          onRetry={sourcingStatus.status === 'FAILED' ? retryMutation.mutate : undefined}
        />
      )}

      {/* JD panel (collapsible) */}
      {search.parsedJd && (
        <div>
          <button
            onClick={() => setJdCollapsed(!jdCollapsed)}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-2"
          >
            <ChevronDown className={cn('h-4 w-4 transition-transform', !jdCollapsed && 'rotate-180')} />
            {jdCollapsed ? 'Show' : 'Hide'} Job Description
          </button>
          {!jdCollapsed && (
            <ParsedJdSummary parsedJd={search.parsedJd} title={search.title} className="animate-fade-in" />
          )}
        </div>
      )}

      {/* Candidates section */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            {pluralize(search.candidateCount, 'Candidate')}
          </h2>
          <div className="flex items-center gap-2">
            <RoleGuard role="RECRUITER">
              <ExportButton searchId={id!} />
            </RoleGuard>
          </div>
        </div>

        <CandidateFiltersBar
          filters={candidateFilters}
          onChange={handleFilterChange}
          onReset={() => setCandidateFilters(DEFAULT_FILTERS)}
        />

        {candidatesLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
          </div>
        ) : !candidatesPage?.content?.length ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <RefreshCw className="h-8 w-8 text-muted-foreground/50 mb-3" />
              <p className="font-medium">No candidates found</p>
              <p className="text-sm text-muted-foreground mt-1">
                {search.candidateCount === 0
                  ? 'Sourcing hasn\'t completed yet, or no candidates matched this JD.'
                  : 'Try adjusting your filters.'}
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {candidatesPage.content.map((candidate) => (
              <CandidateCard key={candidate.id} candidate={candidate} canDelete />
            ))}
            {candidatesPage.totalPages > 1 && (
              <Pagination
                page={candidateFilters.page ?? 0}
                totalPages={candidatesPage.totalPages}
                totalElements={candidatesPage.totalElements}
                pageSize={candidateFilters.size ?? CANDIDATE_PAGE_SIZE}
                onPageChange={(page) => handleFilterChange({ page })}
              />
            )}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title="Delete Search"
        description={`Delete "${search.title}"? All associated candidates will also be removed. This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => deleteMutation.mutateAsync()}
      />
    </div>
  )
}

function SearchDetailSkeleton() {
  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center gap-4">
        <Skeleton className="h-10 w-10 rounded-lg" />
        <div className="space-y-2">
          <Skeleton className="h-7 w-64" />
          <Skeleton className="h-4 w-40" />
        </div>
      </div>
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-32" />)}
      </div>
    </div>
  )
}
