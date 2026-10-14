import { useCountUp } from '@/hooks/useMotion'
import { cn } from '@/lib/utils'

interface ScoreRingProps {
  score: number
  /** Diameter in pixels. */
  size?: number
  strokeWidth?: number
  className?: string
  labelClassName?: string
}

function scoreTone(score: number) {
  if (score >= 70) return { stroke: 'text-emerald-500', text: 'text-emerald-600 dark:text-emerald-400' }
  if (score >= 40) return { stroke: 'text-amber-500', text: 'text-amber-600 dark:text-amber-400' }
  return { stroke: 'text-rose-500', text: 'text-rose-600 dark:text-rose-400' }
}

export function ScoreRing(props: ScoreRingProps) {
  return <Ring {...props} shown={props.score} />
}

/** Same ring, but the number counts up and the arc sweeps in whenever the score changes. */
export function AnimatedScoreRing(props: ScoreRingProps) {
  const shown = useCountUp(props.score)
  return <Ring {...props} shown={shown} />
}

function Ring({ score, shown, size = 40, strokeWidth, className, labelClassName }: ScoreRingProps & { shown: number }) {
  const width = strokeWidth ?? Math.max(3, Math.round(size / 11))
  const radius = (size - width) / 2
  const circumference = 2 * Math.PI * radius
  const clamped = Math.max(0, Math.min(100, shown))
  const tone = scoreTone(score)

  return (
    <div
      className={cn('relative inline-flex shrink-0 items-center justify-center', className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Match score ${score} out of 100`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={width} className="stroke-border" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={width}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped / 100)}
          className={tone.stroke}
        />
      </svg>
      <span
        className={cn('absolute font-semibold tabular-nums', tone.text, labelClassName)}
        style={{ fontSize: Math.max(10, Math.round(size * 0.3)) }}
      >
        {shown}
      </span>
    </div>
  )
}
