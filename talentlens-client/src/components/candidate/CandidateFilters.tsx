import { Search, SlidersHorizontal, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import type { CandidateFilters } from '@/types/candidate'

interface CandidateFiltersBarProps {
  filters: CandidateFilters
  onChange: (changes: Partial<CandidateFilters>) => void
  onReset: () => void
}

export function CandidateFiltersBar({ filters, onChange, onReset }: CandidateFiltersBarProps) {
  const hasFilters = filters.skill || (filters.source && filters.source !== 'ALL') || filters.minScore

  const sortValue = filters.sortBy && filters.sortDir ? `${filters.sortBy}:${filters.sortDir}` : 'matchScore:desc'
  const handleSortChange = (value: string) => {
    const [sortBy, sortDir] = value.split(':') as [CandidateFilters['sortBy'], CandidateFilters['sortDir']]
    onChange({ sortBy, sortDir })
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[180px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Filter by skill…"
          value={filters.skill ?? ''}
          onChange={(e) => onChange({ skill: e.target.value || undefined, page: 0 })}
          className="pl-9"
        />
      </div>

      <Select value={filters.source ?? 'ALL'} onValueChange={(v) => onChange({ source: v === 'ALL' ? undefined : v as CandidateFilters['source'], page: 0 })}>
        <SelectTrigger className="w-40">
          <SelectValue placeholder="All sources" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="ALL">All sources</SelectItem>
          <SelectItem value="GITHUB">GitHub</SelectItem>
          <SelectItem value="STACKOVERFLOW">Stack Overflow</SelectItem>
        </SelectContent>
      </Select>

      <Select value={sortValue} onValueChange={handleSortChange}>
        <SelectTrigger className="w-44">
          <SlidersHorizontal className="h-4 w-4 mr-2 text-muted-foreground" />
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="matchScore:desc">Best match first</SelectItem>
          <SelectItem value="matchScore:asc">Lowest score first</SelectItem>
          <SelectItem value="createdAt:desc">Recently added</SelectItem>
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={onReset} className="gap-1.5 text-muted-foreground">
          <X className="h-3.5 w-3.5" /> Clear
        </Button>
      )}
    </div>
  )
}
