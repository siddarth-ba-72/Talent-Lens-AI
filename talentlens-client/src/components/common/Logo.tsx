import { useId } from 'react'
import { cn } from '@/lib/utils'

export function BrandMark({ className }: { className?: string }) {
  // Gradient ids must be unique per instance, or a second logo on the page reuses the first one's.
  const gradientId = useId()
  return (
    <svg viewBox="0 0 32 32" fill="none" className={cn('h-8 w-8 shrink-0', className)} aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4f46e5" />
          <stop offset="1" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill={`url(#${gradientId})`} />
      <circle cx="14" cy="14" r="6.5" stroke="white" strokeWidth="2.6" />
      <path d="M19 19l4.5 4.5" stroke="white" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="11.8" cy="11.8" r="1.7" fill="white" fillOpacity="0.9" />
    </svg>
  )
}

export function Logo({ className, markClassName }: { className?: string; markClassName?: string }) {
  return (
    <span className={cn('flex items-center gap-2.5 font-semibold text-lg tracking-tight', className)}>
      <BrandMark className={markClassName} />
      <span>
        Talent<span className="gradient-heading">Lens</span>
      </span>
    </span>
  )
}
