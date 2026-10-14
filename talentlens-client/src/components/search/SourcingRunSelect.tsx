import { History } from 'lucide-react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { SourcingStatusResponse } from '@/types/search'
import { formatDateTime, pluralize } from '@/utils/formatters'

interface SourcingRunSelectProps {
  // Completed runs, newest first.
  runs: SourcingStatusResponse[]
  // Unset means the latest run.
  value?: string
  onChange: (runId: string | undefined) => void
}

export function SourcingRunSelect({ runs, value, onChange }: SourcingRunSelectProps) {
  const latest = runs[0]?.runId

  return (
    // Choosing the latest run clears the selection, so the view follows newer runs as they complete.
    <Select value={value ?? latest} onValueChange={(v) => onChange(v === latest ? undefined : v)}>
      <SelectTrigger className="w-auto gap-2" aria-label="Sourcing run">
        <History className="h-4 w-4 text-muted-foreground" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {runs.map((run, index) => (
          <SelectItem key={run.runId} value={run.runId}>
            {index === 0 ? 'Latest' : 'Earlier'} · {formatDateTime(run.completedAt ?? run.startedAt)} ·{' '}
            {pluralize(run.candidatesFound, 'candidate')}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
