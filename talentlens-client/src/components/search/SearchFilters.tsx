import { Search, X, SlidersHorizontal } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { SearchFilters, SearchStatus } from '@/types/search'
import { cn } from '@/lib/utils'

interface SearchFiltersProps {
  filters: SearchFilters
  onChange: (filters: Partial<SearchFilters>) => void
  onReset: () => void
  showStatusFilter?: boolean
}

const SORT_OPTIONS = [
  { value: 'createdAt:desc', label: 'Newest first' },
  { value: 'createdAt:asc', label: 'Oldest first' },
  { value: 'candidateCount:desc', label: 'Most candidates' },
  { value: 'title:asc', label: 'Title A–Z' },
]

const STATUS_OPTIONS: { value: SearchStatus; label: string }[] = [
  { value: 'PENDING', label: 'Pending' },
  { value: 'SOURCING', label: 'Sourcing' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'FAILED', label: 'Failed' },
]

export function SearchFiltersBar({ filters, onChange, onReset, showStatusFilter = true }: SearchFiltersProps) {
  const hasFilters = filters.keyword || (filters.status?.length ?? 0) > 0

  const sortValue = filters.sortBy && filters.sortDir ? `${filters.sortBy}:${filters.sortDir}` : 'createdAt:desc'

  const handleSortChange = (value: string) => {
    const [sortBy, sortDir] = value.split(':') as [SearchFilters['sortBy'], SearchFilters['sortDir']]
    onChange({ sortBy, sortDir })
  }

  const toggleStatus = (status: SearchStatus) => {
    const current = filters.status ?? []
    const next = current.includes(status) ? current.filter((s) => s !== status) : [...current, status]
    onChange({ status: next, page: 0 })
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        {/* Keyword search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by title or keywords…"
            value={filters.keyword ?? ''}
            onChange={(e) => onChange({ keyword: e.target.value || undefined, page: 0 })}
            className="pl-9"
          />
        </div>

        {/* Sort */}
        <Select value={sortValue} onValueChange={handleSortChange}>
          <SelectTrigger className="w-44">
            <SlidersHorizontal className="h-4 w-4 mr-2 text-muted-foreground" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button variant="ghost" size="sm" onClick={onReset} className="gap-1.5 text-muted-foreground">
            <X className="h-3.5 w-3.5" /> Clear
          </Button>
        )}
      </div>

      {/* Status filter chips */}
      {showStatusFilter && (
        <div className="flex flex-wrap gap-2">
          {STATUS_OPTIONS.map(({ value, label }) => {
            const active = filters.status?.includes(value) ?? false
            return (
              <button
                key={value}
                onClick={() => toggleStatus(value)}
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-medium border transition-colors',
                  active
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background text-muted-foreground border-input hover:border-primary/50 hover:text-foreground'
                )}
              >
                {label}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
