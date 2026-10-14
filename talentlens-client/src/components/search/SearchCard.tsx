import { Link } from 'react-router-dom'
import { Calendar, Users, ArrowUpRight, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import type { Search, SearchStatus } from '@/types/search'
import { getSearchStatusColor, getSearchStatusLabel, formatRelativeTime } from '@/utils/formatters'
import { getPlatformMeta } from '@/utils/platforms'
import { cn } from '@/lib/utils'

interface SearchCardProps {
  search: Search
}

const STATUS_DOT: Record<SearchStatus, string> = {
  PENDING: 'bg-amber-500',
  SOURCING: 'bg-blue-500',
  COMPLETED: 'bg-emerald-500',
  FAILED: 'bg-red-500',
}

export function SearchCard({ search }: SearchCardProps) {
  return (
    <Card className="group relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5">
      {/* Accent line that appears on hover */}
      <div className="absolute inset-x-0 top-0 h-0.5 origin-left scale-x-0 bg-brand-gradient transition-transform duration-300 group-hover:scale-x-100" aria-hidden="true" />

      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            {/* The ::after overlay makes the whole card the link target. */}
            <Link
              to={`/searches/${search.id}`}
              className="line-clamp-1 text-base font-semibold transition-colors after:absolute after:inset-0 group-hover:text-primary"
            >
              {search.title}
            </Link>
            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
              {search.parsedJd?.summary ?? 'Processing job description…'}
            </p>
          </div>
          <span className={cn('inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium', getSearchStatusColor(search.status))}>
            <span className="relative flex h-1.5 w-1.5">
              {search.status === 'SOURCING' && (
                <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-75', STATUS_DOT[search.status])} />
              )}
              <span className={cn('relative inline-flex h-1.5 w-1.5 rounded-full', STATUS_DOT[search.status])} />
            </span>
            {getSearchStatusLabel(search.status)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {search.parsedJd?.skills && search.parsedJd.skills.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-1">
            {search.parsedJd.skills.slice(0, 5).map((skill) => (
              <Badge key={skill} variant="secondary" className="text-xs font-normal">
                {skill}
              </Badge>
            ))}
            {search.parsedJd.skills.length > 5 && (
              <Badge variant="outline" className="text-xs font-normal text-muted-foreground">
                +{search.parsedJd.skills.length - 5} more
              </Badge>
            )}
          </div>
        )}

        <div className="flex items-center justify-between border-t pt-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" />
              <span className="font-medium text-foreground">{search.candidateCount}</span>
              {search.candidateCount === 1 ? 'candidate' : 'candidates'}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              {formatRelativeTime(search.createdAt)}
            </span>
            {search.platforms?.map((p) => {
              const { icon: Icon, label } = getPlatformMeta(p)
              return (
                <span key={p} className="flex items-center gap-1 text-xs">
                  <Icon className="h-3 w-3" />
                  {label}
                </span>
              )
            })}
          </div>
          <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground transition-all group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
        </div>
      </CardContent>
    </Card>
  )
}

export function SearchCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-full" />
          </div>
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-3">
        <div className="flex gap-1">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <div className="flex items-center gap-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
      </CardContent>
    </Card>
  )
}

export function SearchCardRefreshing() {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
      Updating…
    </div>
  )
}
