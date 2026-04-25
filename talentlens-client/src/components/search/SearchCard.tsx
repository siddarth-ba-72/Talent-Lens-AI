import { Link } from 'react-router-dom'
import { Calendar, Users, ChevronRight, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { Search } from '@/types/search'
import { getSearchStatusColor, getSearchStatusLabel, formatRelativeTime, pluralize } from '@/utils/formatters'

interface SearchCardProps {
  search: Search
}

export function SearchCard({ search }: SearchCardProps) {
  return (
    <Card className="group transition-all duration-200 hover:shadow-md hover:border-primary/30">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <Link
              to={`/searches/${search.id}`}
              className="text-base font-semibold hover:text-primary transition-colors line-clamp-1"
            >
              {search.title}
            </Link>
            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
              {search.parsedJd?.summary ?? 'Processing job description…'}
            </p>
          </div>
          <span className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getSearchStatusColor(search.status)}`}>
            {getSearchStatusLabel(search.status)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Skills preview */}
        {search.parsedJd?.skills && search.parsedJd.skills.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1">
            {search.parsedJd.skills.slice(0, 5).map((skill) => (
              <Badge key={skill} variant="secondary" className="text-xs">
                {skill}
              </Badge>
            ))}
            {search.parsedJd.skills.length > 5 && (
              <Badge variant="outline" className="text-xs text-muted-foreground">
                +{search.parsedJd.skills.length - 5} more
              </Badge>
            )}
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" />
              {pluralize(search.candidateCount, 'candidate')}
            </span>
            <span className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              {formatRelativeTime(search.createdAt)}
            </span>
          </div>
          <Button asChild variant="ghost" size="sm" className="gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Link to={`/searches/${search.id}`}>
              View <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>

        {/* Platforms */}
        {search.platforms?.length > 0 && (
          <div className="mt-2 flex items-center gap-1.5">
            {search.platforms.map((p) => (
              <span key={p} className="text-xs text-muted-foreground bg-muted rounded px-1.5 py-0.5">
                {p === 'GITHUB' ? 'GitHub' : 'Stack Overflow'}
              </span>
            ))}
          </div>
        )}
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
