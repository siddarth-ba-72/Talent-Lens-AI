import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Check } from 'lucide-react'
import { Logo } from '@/components/common/Logo'
import { ScoreRing } from '@/components/common/ScoreRing'
import { ThemeToggle } from '@/components/common/ThemeToggle'
import { cn } from '@/lib/utils'

interface AuthLayoutProps {
  title: string
  description?: ReactNode
  children: ReactNode
  className?: string
}

export function AuthLayout({ title, description, children, className }: AuthLayoutProps) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[1.05fr_1fr]">
      <BrandPanel />

      <main className="flex flex-col">
        <div className="flex items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" aria-label="TalentLens home" className="lg:invisible">
            <Logo />
          </Link>
          <div className="flex items-center gap-1">
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Home
            </Link>
            <ThemeToggle />
          </div>
        </div>

        <div className="flex flex-1 items-center justify-center px-4 pb-16 pt-4 sm:px-6">
          <div className={cn('w-full max-w-sm animate-fade-up', className)}>
            <h1 className="text-2xl font-semibold">{title}</h1>
            {description && <div className="mt-1.5 text-sm text-muted-foreground">{description}</div>}
            <div className="mt-8">{children}</div>
          </div>
        </div>
      </main>
    </div>
  )
}

const PREVIEW = [
  { name: 'Ana Ruiz', meta: 'GitHub · Go, Python', score: 88 },
  { name: 'Mara Okafor', meta: 'GitHub · Go, Rust', score: 80 },
  { name: 'Ilya Brandt', meta: 'Stack Overflow · postgresql', score: 58 },
]

function BrandPanel() {
  return (
    // `dark` scopes the dark theme tokens to this panel, whatever the page theme is.
    <aside className="dark relative hidden overflow-hidden bg-background p-12 text-foreground lg:flex lg:flex-col lg:justify-between">
      <div className="pointer-events-none absolute inset-0 bg-dot-grid opacity-70" aria-hidden="true" />
      <div className="pointer-events-none absolute -left-32 top-1/4 h-96 w-96 rounded-full bg-primary/30 blur-[120px]" aria-hidden="true" />
      <div className="pointer-events-none absolute -bottom-24 right-0 h-80 w-80 rounded-full bg-cyan-500/20 blur-[110px]" aria-hidden="true" />

      <Link to="/" className="relative w-fit" aria-label="TalentLens home">
        <Logo />
      </Link>

      <div className="relative">
        <h2 className="max-w-md text-3xl font-semibold leading-tight">
          Your next hire already has a <span className="gradient-heading">public track record.</span>
        </h2>
        <p className="mt-4 max-w-md text-muted-foreground">
          TalentLens finds it, reads it against your job description, and shows how every score was reached.
        </p>

        <div className="relative mt-10 max-w-sm">
          <div className="mb-3 flex flex-wrap gap-1.5">
            {['Go', 'Kubernetes', 'PostgreSQL', 'Kafka'].map((s) => (
              <span key={s} className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
                {s}
              </span>
            ))}
          </div>
          <ol className="space-y-2.5">
            {PREVIEW.map((c, i) => (
              <li
                key={c.name}
                className="flex animate-fade-up items-center gap-3 rounded-xl border bg-card/70 px-3.5 py-3 backdrop-blur"
                style={{ animationDelay: `${300 + i * 120}ms`, marginLeft: `${i * 16}px` }}
              >
                <ScoreRing score={c.score} size={38} />
                <div className="min-w-0">
                  <p className="text-sm font-medium">{c.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{c.meta}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>

      <ul className="relative flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
        {['Reads PDF, DOCX and text JDs', 'Sources GitHub and Stack Overflow', 'Explains every score'].map((item) => (
          <li key={item} className="flex items-center gap-2">
            <Check className="h-3.5 w-3.5 text-emerald-400" /> {item}
          </li>
        ))}
      </ul>
    </aside>
  )
}
