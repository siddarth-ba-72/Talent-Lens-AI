import { useState } from 'react'
import { Bell } from 'lucide-react'
import { useShareRequests } from '@/hooks/useShareRequests'
import { cn } from '@/lib/utils'

interface ShareRequestBadgeProps {
  className?: string
}

export function ShareRequestBadge({ className }: ShareRequestBadgeProps) {
  const { data } = useShareRequests('incoming')
  const pending = data?.content?.filter((r) => r.status === 'PENDING').length ?? 0

  if (pending === 0) return <Bell className={cn('h-4 w-4', className)} />

  return (
    <span className={cn('relative inline-flex', className)}>
      <Bell className="h-4 w-4" />
      <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-[9px] font-bold">
        {pending > 9 ? '9+' : pending}
      </span>
    </span>
  )
}
