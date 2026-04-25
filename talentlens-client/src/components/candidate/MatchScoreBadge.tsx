import { cn } from '@/lib/utils'
import { getMatchScoreColor, getMatchScoreBg } from '@/utils/formatters'

interface MatchScoreBadgeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function MatchScoreBadge({ score, size = 'md', showLabel = false, className }: MatchScoreBadgeProps) {
  const color = getMatchScoreColor(score)
  const bg = getMatchScoreBg(score)

  const sizeClasses = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-14 w-14 text-base',
  }

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <div className={cn('rounded-full flex items-center justify-center font-bold', sizeClasses[size], bg, color)}>
        {score}
      </div>
      {showLabel && <span className="text-xs text-muted-foreground">Score</span>}
    </div>
  )
}
