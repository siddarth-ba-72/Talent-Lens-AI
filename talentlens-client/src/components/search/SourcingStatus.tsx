import React from 'react'
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { SourcingTaskStatus } from '@/types/search'
import { getSourcingStatusLabel } from '@/utils/formatters'
import { cn } from '@/lib/utils'

interface SourcingStatusProps {
  status: SourcingTaskStatus
  onRetry?: () => void
  className?: string
}

export function SourcingStatus({ status, onRetry, className }: SourcingStatusProps) {
  const configs: Record<SourcingTaskStatus, { icon: React.ReactNode; bg: string; text: string }> = {
    IDLE: {
      icon: <Clock className="h-4 w-4 text-amber-500" />,
      bg: 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800',
      text: 'text-amber-700 dark:text-amber-300',
    },
    PENDING: {
      icon: <Clock className="h-4 w-4 text-amber-500" />,
      bg: 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800',
      text: 'text-amber-700 dark:text-amber-300',
    },
    IN_PROGRESS: {
      icon: <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />,
      bg: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
      text: 'text-blue-700 dark:text-blue-300',
    },
    COMPLETED: {
      icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
      bg: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800',
      text: 'text-emerald-700 dark:text-emerald-300',
    },
    FAILED: {
      icon: <XCircle className="h-4 w-4 text-red-500" />,
      bg: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
      text: 'text-red-700 dark:text-red-300',
    },
  }

  const config = configs[status]

  return (
    <div className={cn('flex items-center gap-3 rounded-lg border px-4 py-3', config.bg, className)}>
      {config.icon}
      <span className={cn('text-sm font-medium', config.text)}>{getSourcingStatusLabel(status)}</span>
      {status === 'IN_PROGRESS' && (
        <div className="ml-1 flex gap-0.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-blue-500 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      )}
      {status === 'FAILED' && onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="ml-auto h-7 text-xs">
          Retry
        </Button>
      )}
    </div>
  )
}
