import type { SearchStatus, SourcingTaskStatus, Platform } from '@/types/search'
import type { CandidateSource } from '@/types/candidate'

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  return formatDate(iso)
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function getSearchStatusLabel(status: SearchStatus): string {
  const labels: Record<SearchStatus, string> = {
    PENDING: 'Pending',
    SOURCING: 'Sourcing',
    COMPLETED: 'Completed',
    FAILED: 'Failed',
  }
  return labels[status]
}

export function getSearchStatusColor(status: SearchStatus): string {
  const colors: Record<SearchStatus, string> = {
    PENDING: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    SOURCING: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    COMPLETED: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    FAILED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  }
  return colors[status]
}

export function getSourcingStatusLabel(status: SourcingTaskStatus): string {
  const labels: Record<SourcingTaskStatus, string> = {
    IDLE: 'Not started',
    PENDING: 'Queued',
    IN_PROGRESS: 'Finding candidates…',
    COMPLETED: 'Sourcing complete',
    FAILED: 'Sourcing failed',
  }
  return labels[status]
}

export function getPlatformLabel(platform: Platform | CandidateSource): string {
  const labels: Record<string, string> = {
    GITHUB: 'GitHub',
    STACKOVERFLOW: 'Stack Overflow',
  }
  return labels[platform] ?? platform
}

export function getMatchScoreColor(score: number): string {
  if (score >= 70) return 'text-emerald-600 dark:text-emerald-400'
  if (score >= 40) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

export function getMatchScoreBg(score: number): string {
  if (score >= 70) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
  if (score >= 40) return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
  return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
}

export function getInitials(name: string | null | undefined): string {
  if (!name) return '?'
  return name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()
}

export function pluralize(count: number, singular: string, plural?: string): string {
  return count === 1 ? `${count} ${singular}` : `${count} ${plural ?? singular + 's'}`
}
