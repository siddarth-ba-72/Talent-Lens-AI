import { useState, type ReactNode } from 'react'
import { Briefcase, Check, Clock, Lock, UserRound, Users, X } from 'lucide-react'
import { cn } from '@/lib/utils'

type Role = 'recruiter' | 'manager'

const CAPABILITIES: Record<Role, { title: string; body: string }[]> = {
  recruiter: [
    { title: 'Start from the JD', body: 'Paste it or upload a PDF, DOCX or text file, then review what was extracted before sourcing.' },
    { title: 'Source and re-source', body: 'Run searches on GitHub and Stack Overflow. Every run is kept, so you can compare them.' },
    { title: 'Curate the shortlist', body: 'Filter by skill, platform or minimum score, remove poor fits, and export to CSV or JSON.' },
    { title: 'Decide who sees what', body: 'Approve or reject hiring managers who ask for access to a search.' },
  ],
  manager: [
    { title: 'See what was shared', body: 'Searches a recruiter has shared with you show up on your dashboard.' },
    { title: 'Read the reasoning', body: 'Browse ranked candidates with their skills, experience and score breakdown.' },
    { title: 'Ask for access', body: 'Find a recruiter, pick their search, and send a request in a couple of clicks.' },
    { title: 'Nothing to break', body: 'Your access is read-only, so the recruiter’s search stays exactly as they left it.' },
  ],
}

export function RolesShowcase() {
  const [role, setRole] = useState<Role>('recruiter')

  return (
    <div className="space-y-8">
      <div className="flex justify-center">
        <div className="inline-flex rounded-xl border bg-muted/50 p-1" role="tablist" aria-label="Role">
          {(
            [
              { id: 'recruiter', label: 'Recruiter', icon: Briefcase },
              { id: 'manager', label: 'Hiring manager', icon: Users },
            ] as const
          ).map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={role === id}
              onClick={() => setRole(id)}
              className={cn(
                'inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all',
                role === id ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>
      </div>

      <div key={role} className="grid animate-fade-in items-center gap-8 lg:grid-cols-2" role="tabpanel">
        <ul className="grid gap-4 sm:grid-cols-2">
          {CAPABILITIES[role].map(({ title, body }) => (
            <li key={title} className="rounded-xl border bg-card p-4 transition-colors hover:border-primary/30">
              <p className="flex items-center gap-2 text-sm font-semibold">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Check className="h-3 w-3" strokeWidth={3} />
                </span>
                {title}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</p>
            </li>
          ))}
        </ul>
        {role === 'recruiter' ? <RecruiterMock /> : <ManagerMock />}
      </div>
    </div>
  )
}

function MockFrame({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="relative">
      <div className="absolute -inset-3 rounded-[1.75rem] bg-brand-gradient opacity-10 blur-xl" aria-hidden="true" />
      <div className="relative rounded-2xl border bg-card shadow-xl shadow-primary/5">
        <div className="flex items-center justify-between border-b px-5 py-3">
          <p className="text-sm font-semibold">{title}</p>
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Try it</span>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

function RecruiterMock() {
  const [decision, setDecision] = useState<'pending' | 'approved' | 'rejected'>('pending')
  return (
    <MockFrame title="Share requests">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-cyan-500/15 text-sm font-semibold text-cyan-700 dark:text-cyan-300">
          DK
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm">
            <span className="font-medium">Dana K.</span> <span className="text-muted-foreground">· Hiring manager</span>
          </p>
          <p className="text-sm text-muted-foreground">
            wants to view <span className="font-medium text-foreground">Senior Backend Engineer</span>
          </p>
          <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" /> 12 minutes ago
          </p>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-2">
        {decision === 'pending' ? (
          <>
            <button
              type="button"
              onClick={() => setDecision('approved')}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90 active:scale-[0.98]"
            >
              <Check className="h-4 w-4" /> Approve
            </button>
            <button
              type="button"
              onClick={() => setDecision('rejected')}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium transition hover:bg-accent active:scale-[0.98]"
            >
              <X className="h-4 w-4" /> Reject
            </button>
          </>
        ) : (
          <div className="flex w-full animate-fade-in items-center justify-between rounded-lg border bg-muted/40 px-3 py-2">
            <span
              className={cn(
                'inline-flex items-center gap-1.5 text-sm font-medium',
                decision === 'approved' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400',
              )}
            >
              {decision === 'approved' ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
              {decision === 'approved' ? 'Approved. Dana can now see this search.' : 'Rejected'}
            </span>
            <button type="button" onClick={() => setDecision('pending')} className="text-xs text-muted-foreground hover:text-foreground">
              Undo
            </button>
          </div>
        )}
      </div>
    </MockFrame>
  )
}

function ManagerMock() {
  const [requested, setRequested] = useState(false)
  const searches = [
    { title: 'Senior Backend Engineer', owner: 'Alex P.', count: 24 },
    { title: 'ML Engineer', owner: 'Alex P.', count: 17 },
  ]
  return (
    <MockFrame title="Shared with you">
      <ul className="space-y-2">
        {searches.map((s) => (
          <li key={s.title} className="flex items-center gap-3 rounded-lg border px-3 py-2.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{s.title}</p>
              <p className="text-xs text-muted-foreground">Shared by {s.owner}</p>
            </div>
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <UserRound className="h-3 w-3" /> {s.count}
            </span>
          </li>
        ))}
        <li className="flex items-center gap-3 rounded-lg border border-dashed px-3 py-2.5">
          <Lock className="h-3.5 w-3.5 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-muted-foreground">Lead Frontend Engineer</p>
            <p className="text-xs text-muted-foreground">Owned by Alex P.</p>
          </div>
          {requested ? (
            <button
              type="button"
              onClick={() => setRequested(false)}
              className="inline-flex animate-pop items-center gap-1 rounded-full bg-amber-500/15 px-2.5 py-1 text-xs font-medium text-amber-700 dark:text-amber-300"
              title="Cancel (demo)"
            >
              <Clock className="h-3 w-3" /> Pending
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setRequested(true)}
              className="rounded-lg bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground transition hover:bg-primary/90 active:scale-95"
            >
              Request access
            </button>
          )}
        </li>
      </ul>
    </MockFrame>
  )
}
