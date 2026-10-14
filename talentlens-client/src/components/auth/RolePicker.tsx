import { Briefcase, Check, Users } from 'lucide-react'
import type { UserRole } from '@/types/auth'
import { cn } from '@/lib/utils'

const ROLES: { value: UserRole; label: string; description: string; icon: typeof Briefcase }[] = [
  { value: 'RECRUITER', label: 'Recruiter', description: 'I run searches and build shortlists', icon: Briefcase },
  { value: 'HIRING_MANAGER', label: 'Hiring manager', description: 'I review shortlists shared with me', icon: Users },
]

interface RolePickerProps {
  value: UserRole | '' | undefined
  onChange: (role: UserRole) => void
}

export function RolePicker({ value, onChange }: RolePickerProps) {
  return (
    <div className="grid grid-cols-2 gap-2.5" role="radiogroup" aria-label="Role">
      {ROLES.map(({ value: role, label, description, icon: Icon }) => {
        const selected = value === role
        return (
          <button
            key={role}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(role)}
            className={cn(
              'relative rounded-xl border p-3 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              selected ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'hover:border-primary/40 hover:bg-accent/40',
            )}
          >
            <span
              className={cn(
                'mb-2 flex h-8 w-8 items-center justify-center rounded-lg transition-colors',
                selected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
            </span>
            <span className="block text-sm font-medium">{label}</span>
            <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{description}</span>
            {selected && (
              <span className="absolute right-2.5 top-2.5 flex h-4 w-4 animate-pop items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Check className="h-2.5 w-2.5" strokeWidth={3} />
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
