import { useState } from 'react'
import { exportCandidates } from '@/api/candidateApi'
import type { CandidateFilters } from '@/types/candidate'
import { useUiStore } from '@/stores/uiStore'

export function useExport(searchId: string) {
  const [isExporting, setIsExporting] = useState(false)
  const addToast = useUiStore((s) => s.addToast)

  const triggerDownload = async (format: 'csv' | 'json', filters?: CandidateFilters) => {
    setIsExporting(true)
    try {
      const blob = await exportCandidates(searchId, format, filters)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `candidates-${searchId}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 100)
      addToast({ type: 'success', title: 'Export started', description: `Downloading as ${format.toUpperCase()}` })
    } catch {
      addToast({ type: 'error', title: 'Export failed', description: 'Please try again.' })
    } finally {
      setIsExporting(false)
    }
  }

  return {
    exportCsv: (filters?: CandidateFilters) => triggerDownload('csv', filters),
    exportJson: (filters?: CandidateFilters) => triggerDownload('json', filters),
    isExporting,
  }
}
