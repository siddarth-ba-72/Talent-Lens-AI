import { useState } from 'react'
import { Check } from 'lucide-react'
import { AnimatedScoreRing } from '@/components/common/ScoreRing'
import { cn } from '@/lib/utils'
import { DEMO_ROLES, LEVELS, experienceMatch, jdSkills, matchScore, skillMatch, type Level } from './demoData'

const ROLE = DEMO_ROLES[0]
const ROLE_SKILLS = jdSkills(ROLE)

export function ScorePlayground() {
  const [owned, setOwned] = useState<string[]>(['Go', 'Python', 'PostgreSQL', 'Kafka'])
  const [level, setLevel] = useState<Level>('Mid')

  const skill = skillMatch(ROLE_SKILLS, owned)
  const experience = experienceMatch(ROLE.level, level)
  const score = matchScore(skill, experience)

  const toggle = (s: string) => setOwned((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]))

  return (
    <div className="grid overflow-hidden rounded-2xl border bg-card shadow-xl shadow-primary/5 lg:grid-cols-[1.15fr_1fr]">
      {/* Controls */}
      <div className="space-y-7 p-6 sm:p-8">
        <div>
          <p className="text-sm font-medium">
            The role asks for <span className="text-muted-foreground">({ROLE.title})</span>
          </p>
          <p className="mb-3 text-xs text-muted-foreground">Tap the skills this candidate has.</p>
          <div className="flex flex-wrap gap-2">
            {ROLE_SKILLS.map((s) => {
              const on = owned.includes(s)
              return (
                <button
                  key={s}
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggle(s)}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-all active:scale-95',
                    on
                      ? 'border-primary/40 bg-primary/10 text-primary'
                      : 'border-dashed text-muted-foreground hover:border-primary/40 hover:text-foreground',
                  )}
                >
                  <span
                    className={cn(
                      'flex h-4 w-4 items-center justify-center rounded-full border transition-colors',
                      on ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground/40',
                    )}
                  >
                    {on && <Check className="h-2.5 w-2.5" strokeWidth={3} />}
                  </span>
                  {s}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <p className="text-sm font-medium">
            Candidate seniority <span className="text-muted-foreground">(role wants {ROLE.level})</span>
          </p>
          <p className="mb-3 text-xs text-muted-foreground">Inferred from their profile; unknown counts as a coin flip.</p>
          <div className="inline-flex flex-wrap gap-1 rounded-xl border bg-muted/50 p-1" role="radiogroup" aria-label="Candidate seniority">
            {LEVELS.map((l) => (
              <button
                key={l}
                type="button"
                role="radio"
                aria-checked={l === level}
                onClick={() => setLevel(l)}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-sm font-medium transition-all',
                  l === level ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {l}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Result */}
      <div className="relative flex flex-col items-center justify-center gap-6 border-t bg-muted/30 p-6 sm:p-8 lg:border-l lg:border-t-0">
        <div className="pointer-events-none absolute inset-0 bg-dot-grid opacity-60" aria-hidden="true" />
        <div className="relative flex flex-col items-center gap-2">
          <AnimatedScoreRing score={score} size={136} strokeWidth={11} />
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Match score</span>
        </div>

        <div className="relative w-full max-w-xs space-y-3">
          <Bar label="Skill match" weight="60%" value={skill} />
          <Bar label="Experience match" weight="40%" value={experience} />
        </div>

        <p className="relative rounded-lg border bg-background/80 px-3 py-2 font-mono text-xs text-muted-foreground">
          0.6 × {skill} + 0.4 × {experience} = <span className="font-semibold text-foreground">{score}</span>
        </p>
      </div>
    </div>
  )
}

function Bar({ label, weight, value }: { label: string; weight: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="font-medium">
          {label} <span className="font-normal text-muted-foreground">· weight {weight}</span>
        </span>
        <span className="font-mono tabular-nums text-muted-foreground">{value}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-border/70">
        <div className="h-full rounded-full bg-brand-gradient transition-[width] duration-500 ease-out" style={{ width: `${value}%` }} />
      </div>
    </div>
  )
}
