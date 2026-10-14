import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, GitBranch, Hash, Loader2, Play, RotateCcw } from 'lucide-react'
import { AnimatedScoreRing } from '@/components/common/ScoreRing'
import { useInView, usePrefersReducedMotion } from '@/hooks/useMotion'
import { cn } from '@/lib/utils'
import { DEMO_ROLES, jdSkills, parseJd, rankCandidates, type RankedCandidate } from './demoData'

type Phase = 'idle' | 'parsing' | 'sourcing' | 'ranked'

const SKILL_STEP_MS = 170

export function LiveDemo() {
  const reduced = usePrefersReducedMotion()
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.3 })
  const [roleIndex, setRoleIndex] = useState(0)
  const [phase, setPhase] = useState<Phase>('idle')
  const [parsed, setParsed] = useState(0)
  const [sourced, setSourced] = useState(0)
  const [expanded, setExpanded] = useState<string | null>(null)
  // Mutated in place (never reassigned) so the unmount cleanup sees every pending timer.
  const timers = useRef<number[]>([])
  const started = useRef(false)

  const role = DEMO_ROLES[roleIndex]
  const skills = useMemo(() => jdSkills(role), [role])
  const segments = useMemo(() => parseJd(role.jd), [role])
  const ranked = useMemo(() => rankCandidates(role), [role])

  const run = useCallback(
    (index: number) => {
      timers.current.splice(0).forEach(clearTimeout)
      const at = (ms: number, fn: () => void) => timers.current.push(window.setTimeout(fn, ms))
      const target = DEMO_ROLES[index]
      const count = jdSkills(target).length
      const top = rankCandidates(target)[0]?.handle ?? null

      setRoleIndex(index)
      setExpanded(null)
      if (reduced) {
        setParsed(count)
        setSourced(2)
        setPhase('ranked')
        setExpanded(top)
        return
      }

      setPhase('parsing')
      setParsed(0)
      setSourced(0)
      for (let i = 1; i <= count; i++) at(i * SKILL_STEP_MS, () => setParsed(i))
      const sourceAt = count * SKILL_STEP_MS + 350
      at(sourceAt, () => setPhase('sourcing'))
      at(sourceAt + 700, () => setSourced(1))
      at(sourceAt + 1300, () => setSourced(2))
      at(sourceAt + 1650, () => {
        setPhase('ranked')
        setExpanded(top)
      })
    },
    [reduced],
  )

  // Play once on its own the first time the demo is on screen.
  useEffect(() => {
    if (!inView || started.current) return
    started.current = true
    const id = window.setTimeout(() => run(0), 400)
    return () => clearTimeout(id)
  }, [inView, run])

  useEffect(() => {
    const pending = timers.current
    return () => pending.forEach(clearTimeout)
  }, [])

  const busy = phase === 'parsing' || phase === 'sourcing'
  const skillsShown = phase === 'idle' ? 0 : phase === 'parsing' ? parsed : skills.length

  return (
    <div ref={ref} className="relative">
      {/* Halo behind the window */}
      <div className="absolute -inset-4 rounded-[2rem] bg-brand-gradient opacity-20 blur-2xl dark:opacity-25" aria-hidden="true" />

      <div className="relative overflow-hidden rounded-2xl border bg-card/90 shadow-2xl shadow-primary/10 backdrop-blur">
        {/* Window chrome */}
        <div className="flex items-center gap-3 border-b bg-muted/40 px-4 py-2.5">
          <div className="flex gap-1.5" aria-hidden="true">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
          </div>
          <span className="min-w-0 truncate text-xs font-medium text-muted-foreground">New search · {role.title}</span>
          <span className="ml-auto shrink-0 whitespace-nowrap rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Sample data
          </span>
        </div>

        <div className="space-y-4 p-4 sm:p-5">
          {/* Role picker + run */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex rounded-lg border bg-muted/50 p-0.5" role="group" aria-label="Sample role">
              {DEMO_ROLES.map((r, i) => (
                <button
                  key={r.id}
                  type="button"
                  aria-pressed={i === roleIndex}
                  onClick={() => run(i)}
                  className={cn(
                    'rounded-md px-3 py-1 text-xs font-medium transition-all',
                    i === roleIndex ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={() => run(roleIndex)}
              disabled={busy}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:opacity-60"
            >
              {busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : phase === 'ranked' ? (
                <RotateCcw className="h-3.5 w-3.5" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
              {busy ? 'Running' : phase === 'ranked' ? 'Run again' : 'Run'}
            </button>
          </div>

          {/* Job description with skills lighting up as they're extracted */}
          <div className="rounded-xl border bg-background/60 p-3.5">
            <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Job description</p>
            <p className="text-[13px] leading-relaxed text-muted-foreground">
              {segments.map((segment, i) => {
                if (segment.order === undefined) return <span key={i}>{segment.text}</span>
                const lit = segment.order < skillsShown
                return (
                  <mark
                    key={i}
                    className={cn(
                      'rounded px-0.5 transition-colors duration-300',
                      lit ? 'bg-primary/15 font-medium text-primary' : 'bg-transparent text-muted-foreground',
                    )}
                  >
                    {segment.text}
                  </mark>
                )
              })}
            </p>
          </div>

          {/* Extracted requirements */}
          <div className="flex min-h-[28px] flex-wrap items-center gap-1.5">
            {skills.slice(0, skillsShown).map((skill) => (
              <span key={`${role.id}-${skill}`} className="animate-pop rounded-full border border-primary/25 bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                {skill}
              </span>
            ))}
            {skillsShown === skills.length && phase !== 'idle' && (
              <span className="animate-pop rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 text-xs font-medium text-cyan-700 dark:text-cyan-300">
                {role.level}
              </span>
            )}
            {phase === 'idle' && <span className="text-xs text-muted-foreground">Extracted skills appear here.</span>}
          </div>

          <Stepper phase={phase} />

          {/* Results */}
          <div className="min-h-[352px]" aria-live="polite">
            {phase === 'idle' && (
              <div className="flex h-[352px] flex-col items-center justify-center gap-3 rounded-xl border border-dashed text-center">
                <p className="text-sm text-muted-foreground">Pick a role and press Run.</p>
              </div>
            )}
            {phase === 'parsing' && (
              <div className="space-y-2" aria-label="Reading the job description">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className="shimmer h-[62px] rounded-xl opacity-60" />
                ))}
              </div>
            )}
            {phase === 'sourcing' && <SourcingProgress sourced={sourced} />}
            {phase === 'ranked' && (
              <ol className="space-y-2">
                {ranked.map((candidate, i) => (
                  <li key={`${role.id}-${candidate.handle}`} className="animate-fade-up" style={{ animationDelay: `${i * 90}ms` }}>
                    <CandidateRow
                      candidate={candidate}
                      open={expanded === candidate.handle}
                      onToggle={() => setExpanded((cur) => (cur === candidate.handle ? null : candidate.handle))}
                    />
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Stepper({ phase }: { phase: Phase }) {
  const order: Phase[] = ['parsing', 'sourcing', 'ranked']
  const current = order.indexOf(phase)
  const steps = ['Parse JD', 'Source', 'Rank']
  return (
    <div className="flex items-center gap-2">
      {steps.map((label, i) => {
        const done = current > i || phase === 'ranked'
        const active = current === i && phase !== 'ranked'
        return (
          <div key={label} className="flex flex-1 items-center gap-2">
            <span
              className={cn(
                'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold transition-colors',
                done && 'border-emerald-500 bg-emerald-500 text-white',
                active && 'border-primary text-primary',
                !done && !active && 'text-muted-foreground',
              )}
            >
              {done ? <Check className="h-3 w-3" /> : active ? <Loader2 className="h-3 w-3 animate-spin" /> : i + 1}
            </span>
            <span className={cn('text-xs font-medium', done || active ? 'text-foreground' : 'text-muted-foreground')}>{label}</span>
            {i < steps.length - 1 && (
              <span className="relative h-px flex-1 overflow-hidden bg-border">
                <span className={cn('absolute inset-y-0 left-0 bg-emerald-500 transition-all duration-500', done ? 'w-full' : 'w-0')} />
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function SourcingProgress({ sourced }: { sourced: number }) {
  const platforms = [
    { label: 'GitHub', detail: 'Searching users by language and repo topics', icon: GitBranch },
    { label: 'Stack Overflow', detail: 'Searching top answerers by tag', icon: Hash },
  ]
  return (
    <div className="flex h-[352px] flex-col justify-center gap-3">
      {platforms.map(({ label, detail, icon: Icon }, i) => {
        const done = sourced > i
        return (
          <div key={label} className="rounded-xl border bg-background/60 p-3.5">
            <div className="flex items-center gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{label}</p>
                <p className="truncate text-xs text-muted-foreground">{detail}</p>
              </div>
              {done ? <Check className="h-4 w-4 text-emerald-500" /> : <Loader2 className="h-4 w-4 animate-spin text-primary" />}
            </div>
            <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted">
              <div className={cn('h-full rounded-full bg-brand-gradient', done ? 'w-full' : 'animate-progress-fill')} />
            </div>
          </div>
        )
      })}
      <p className="text-center text-xs text-muted-foreground">Scoring profiles against the extracted requirements…</p>
    </div>
  )
}

function CandidateRow({ candidate, open, onToggle }: { candidate: RankedCandidate; open: boolean; onToggle: () => void }) {
  const SourceIcon = candidate.source === 'GITHUB' ? GitBranch : Hash
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      className={cn(
        'w-full rounded-xl border bg-background/60 px-3 py-2.5 text-left transition-all hover:border-primary/40 hover:bg-background',
        open && 'border-primary/40 bg-background shadow-sm',
      )}
    >
      <div className="flex items-center gap-3">
        <AnimatedScoreRing score={candidate.score} size={40} />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <span className="truncate text-sm font-medium">{candidate.name}</span>
            <span className="hidden truncate font-mono text-[11px] text-muted-foreground sm:inline">@{candidate.handle}</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <SourceIcon className="h-3 w-3 shrink-0" />
            <span className="truncate">{candidate.signal}</span>
            <span aria-hidden="true">·</span>
            <span className="shrink-0">{candidate.level}</span>
          </div>
        </div>
        <ChevronDown className={cn('h-4 w-4 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')} />
      </div>
      {open && (
        <div className="mt-3 space-y-2 border-t pt-3 animate-fade-in">
          <div className="flex flex-wrap gap-1">
            {candidate.matched.map((s) => (
              <span key={s} className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[11px] font-medium text-emerald-700 dark:text-emerald-300">
                <Check className="h-3 w-3" />
                {s}
              </span>
            ))}
            {candidate.missing.map((s) => (
              <span key={s} className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground line-through decoration-muted-foreground/50">
                {s}
              </span>
            ))}
          </div>
          <p className="font-mono text-[11px] text-muted-foreground">
            0.6 × {candidate.skill} skills + 0.4 × {candidate.experience} experience ={' '}
            <span className="font-semibold text-foreground">{candidate.score}</span>
          </p>
        </div>
      )}
    </button>
  )
}
