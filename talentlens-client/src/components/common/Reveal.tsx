import type { CSSProperties, ReactNode } from 'react'
import { useInView } from '@/hooks/useMotion'
import { cn } from '@/lib/utils'

interface RevealProps {
  children: ReactNode
  delayMs?: number
  className?: string
}

/** Fades and lifts its content in the first time it scrolls into view. */
export function Reveal({ children, delayMs = 0, className }: RevealProps) {
  const { ref, inView } = useInView<HTMLDivElement>()
  return (
    <div
      ref={ref}
      data-visible={inView}
      className={cn('reveal', className)}
      style={{ '--reveal-delay': `${delayMs}ms` } as CSSProperties}
    >
      {children}
    </div>
  )
}
