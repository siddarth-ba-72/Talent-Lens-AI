import { GitBranch, Hash } from 'lucide-react'
import type { Platform } from '@/types/search'
import { cn } from '@/lib/utils'

interface PlatformSelectorProps {
  value: Platform[]
  onChange: (platforms: Platform[]) => void
  error?: string
}

const PLATFORMS: { id: Platform; label: string; description: string; icon: React.ReactNode }[] = [
  {
    id: 'GITHUB',
    label: 'GitHub',
    description: 'Find developers by repos, languages & activity',
    icon: <GitBranch className="h-5 w-5" />,
  },
  {
    id: 'STACKOVERFLOW',
    label: 'Stack Overflow',
    description: 'Find top answerers by tag & reputation',
    icon: <Hash className="h-5 w-5" />,
  },
]

export function PlatformSelector({ value, onChange, error }: PlatformSelectorProps) {
  const toggle = (platform: Platform) => {
    if (value.includes(platform)) {
      onChange(value.filter((p) => p !== platform))
    } else {
      onChange([...value, platform])
    }
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {PLATFORMS.map(({ id, label, description, icon }) => {
          const selected = value.includes(id)
          return (
            <button
              key={id}
              type="button"
              onClick={() => toggle(id)}
              className={cn(
                'flex items-center gap-3 rounded-lg border-2 p-4 text-left transition-all',
                selected
                  ? 'border-primary bg-primary/5 text-foreground'
                  : 'border-border hover:border-primary/40 text-muted-foreground hover:text-foreground'
              )}
            >
              <div className={cn('rounded-md p-2', selected ? 'bg-primary/10 text-primary' : 'bg-muted')}>
                {icon}
              </div>
              <div>
                <p className={cn('font-medium text-sm', selected ? 'text-foreground' : '')}>{label}</p>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
              <div className={cn(
                'ml-auto h-5 w-5 rounded-full border-2 transition-all shrink-0',
                selected ? 'border-primary bg-primary' : 'border-muted-foreground/30'
              )}>
                {selected && (
                  <svg viewBox="0 0 20 20" fill="white" className="h-4 w-4 m-0.5">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </div>
            </button>
          )
        })}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
