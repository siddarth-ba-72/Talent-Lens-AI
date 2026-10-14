import { Sparkles } from 'lucide-react'
import type { Platform } from '@/types/search'
import { usePlatforms } from '@/hooks/usePlatforms'
import { PLATFORM_GROUPS, PLATFORM_META, PLATFORMS } from '@/utils/platforms'
import { cn } from '@/lib/utils'

interface PlatformSelectorProps {
  value: Platform[]
  onChange: (platforms: Platform[]) => void
  // When on, the server picks the platforms that suit the JD and `value` is ignored.
  auto: boolean
  onAutoChange: (auto: boolean) => void
  error?: string
}

export function PlatformSelector({ value, onChange, auto, onAutoChange, error }: PlatformSelectorProps) {
  const { isAvailable } = usePlatforms()

  const toggle = (platform: Platform) => {
    if (value.includes(platform)) {
      onChange(value.filter((p) => p !== platform))
    } else {
      onChange([...value, platform])
    }
  }

  return (
    <div className="space-y-4">
      <button
        type="button"
        role="switch"
        aria-checked={auto}
        onClick={() => onAutoChange(!auto)}
        className={cn(
          'flex w-full items-center gap-3 rounded-lg border-2 p-4 text-left transition-all',
          auto ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/40'
        )}
      >
        <div className={cn('rounded-md p-2', auto ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground')}>
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="font-medium text-sm">Recommended for this JD</p>
          <p className="text-xs text-muted-foreground">
            GitHub, Stack Overflow and Hacker News, plus the sources that suit the role (e.g. Hugging Face for ML, npm
            for JavaScript)
          </p>
        </div>
        <span
          aria-hidden
          className={cn(
            'ml-auto inline-flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors',
            auto ? 'bg-primary' : 'bg-muted-foreground/30'
          )}
        >
          <span className={cn('h-4 w-4 rounded-full bg-white transition-transform', auto && 'translate-x-4')} />
        </span>
      </button>

      {!auto && (
        <div className="space-y-4">
          {PLATFORM_GROUPS.map((group) => {
            const platforms = PLATFORMS.filter((platform) => PLATFORM_META[platform].group === group)
            return (
              <div key={group} className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{group}</p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {platforms.map((id) => {
                    const { label, description, icon: Icon } = PLATFORM_META[id]
                    const available = isAvailable(id)
                    const selected = available && value.includes(id)
                    return (
                      <button
                        key={id}
                        type="button"
                        disabled={!available}
                        onClick={() => toggle(id)}
                        className={cn(
                          'flex items-center gap-3 rounded-lg border-2 p-4 text-left transition-all',
                          !available && 'cursor-not-allowed opacity-50',
                          selected
                            ? 'border-primary bg-primary/5 text-foreground'
                            : 'border-border text-muted-foreground',
                          available && !selected && 'hover:border-primary/40 hover:text-foreground'
                        )}
                      >
                        <div className={cn('rounded-md p-2', selected ? 'bg-primary/10 text-primary' : 'bg-muted')}>
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="min-w-0">
                          <p className={cn('font-medium text-sm', selected ? 'text-foreground' : '')}>{label}</p>
                          <p className="text-xs text-muted-foreground">
                            {available ? description : 'Not configured on this server'}
                          </p>
                        </div>
                        <div
                          className={cn(
                            'ml-auto h-5 w-5 rounded-full border-2 transition-all shrink-0',
                            selected ? 'border-primary bg-primary' : 'border-muted-foreground/30'
                          )}
                        >
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
              </div>
            )
          })}
        </div>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
