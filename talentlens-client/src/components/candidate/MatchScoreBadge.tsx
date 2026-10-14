import { ScoreRing } from '@/components/common/ScoreRing'
import { cn } from '@/lib/utils'

interface MatchScoreBadgeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

const SIZES = { sm: 38, md: 46, lg: 60 }

export function MatchScoreBadge({ score, size = 'md', showLabel = false, className }: MatchScoreBadgeProps) {
  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <ScoreRing score={score} size={SIZES[size]} />
      {showLabel && <span className="text-xs text-muted-foreground">Score</span>}
    </div>
  )
}
