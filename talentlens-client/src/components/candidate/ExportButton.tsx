import { useState } from 'react'
import { Download, ChevronDown, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useExport } from '@/hooks/useExport'
import { cn } from '@/lib/utils'

interface ExportButtonProps {
  searchId: string
}

export function ExportButton({ searchId }: ExportButtonProps) {
  const [open, setOpen] = useState(false)
  const { exportCsv, exportJson, isExporting } = useExport(searchId)

  return (
    <div className="relative">
      <div className="flex rounded-lg overflow-hidden border border-input">
        <Button
          variant="outline"
          size="sm"
          className="rounded-none border-0 border-r gap-1.5 px-3"
          onClick={exportCsv}
          disabled={isExporting}
        >
          {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
          Export CSV
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="rounded-none border-0 px-2"
          onClick={() => setOpen(!open)}
          disabled={isExporting}
        >
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} />
        </Button>
      </div>
      {open && (
        <div className="absolute right-0 top-full mt-1 rounded-lg border bg-popover shadow-lg z-10 py-1 min-w-[140px]">
          <button
            onClick={() => { exportCsv(); setOpen(false) }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <Download className="h-3.5 w-3.5" /> Export CSV
          </button>
          <button
            onClick={() => { exportJson(); setOpen(false) }}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <Download className="h-3.5 w-3.5" /> Export JSON
          </button>
        </div>
      )}
    </div>
  )
}
