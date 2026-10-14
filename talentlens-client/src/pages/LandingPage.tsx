import { useEffect, useState, type PointerEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, BarChart3, FileText, GitBranch, Hash, Radar, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/common/Logo'
import { Reveal } from '@/components/common/Reveal'
import { ThemeToggle } from '@/components/common/ThemeToggle'
import { LiveDemo } from '@/components/landing/LiveDemo'
import { ScorePlayground } from '@/components/landing/ScorePlayground'
import { RolesShowcase } from '@/components/landing/RolesShowcase'
import { cn } from '@/lib/utils'

export default function LandingPage() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <LandingNav />
      <Hero />
      <HowItWorks />
      <Scoring />
      <Roles />
      <FinalCta />
      <Footer />
    </div>
  )
}

function LandingNav() {
  const [scrolled, setScrolled] = useState(() => window.scrollY > 8)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-50 border-b transition-all duration-300',
        scrolled ? 'border-border bg-background/75 backdrop-blur-lg' : 'border-transparent bg-transparent',
      )}
    >
      <div className="container mx-auto flex h-16 items-center justify-between gap-4">
        <Link to="/" aria-label="TalentLens home">
          <Logo />
        </Link>
        <nav className="hidden items-center gap-1 md:flex">
          {[
            ['#how', 'How it works'],
            ['#scoring', 'Scoring'],
            ['#roles', 'Roles'],
          ].map(([href, label]) => (
            <a key={href} href={href} className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground">
              {label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link to="/login">Sign in</Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/register">Get started</Link>
          </Button>
        </div>
      </div>
    </header>
  )
}

function Hero() {
  // The spotlight follows the pointer by updating CSS variables directly, without re-rendering.
  const onPointerMove = (e: PointerEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.setProperty('--x', `${e.clientX - rect.left}px`)
    e.currentTarget.style.setProperty('--y', `${e.clientY - rect.top}px`)
  }

  return (
    <section onPointerMove={onPointerMove} className="relative isolate pb-20 pt-28 sm:pt-32 lg:pb-28">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-dot-grid" aria-hidden="true" />
      <div className="spotlight pointer-events-none absolute inset-0 -z-10" aria-hidden="true" />

      <div className="container mx-auto grid grid-cols-1 items-center gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-12">
        <div className="max-w-xl">
          <a
            href="#how"
            className="group mb-6 inline-flex animate-fade-up items-center gap-2 rounded-full border bg-background/70 py-1 pl-1 pr-3 text-xs font-medium text-muted-foreground backdrop-blur transition-colors hover:border-primary/40 hover:text-foreground"
          >
            <span className="inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full bg-primary/10 px-2 py-0.5 text-primary">
              <Sparkles className="h-3 w-3" /> AI sourcing
            </span>
            <span className="sm:hidden">Ranked against your JD</span>
            <span className="hidden sm:inline">GitHub and Stack Overflow, ranked against your JD</span>
            <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
          </a>

          <h1 className="animate-fade-up text-4xl font-semibold leading-[1.08] sm:text-5xl lg:text-[3.4rem]" style={{ animationDelay: '60ms' }}>
            Hire from what developers have <span className="gradient-heading">actually built.</span>
          </h1>

          <p className="mt-5 animate-fade-up text-lg leading-relaxed text-muted-foreground" style={{ animationDelay: '120ms' }}>
            Paste a job description. TalentLens pulls out the skills it is really asking for, searches public developer
            profiles, and ranks everyone it finds with a score you can check.
          </p>

          <div className="mt-8 flex animate-fade-up flex-wrap items-center gap-3" style={{ animationDelay: '180ms' }}>
            <Button asChild size="lg" className="group shadow-lg shadow-primary/25">
              <Link to="/register">
                Start a search
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="bg-background/70 backdrop-blur">
              <Link to="/login">Sign in</Link>
            </Button>
          </div>

          <dl className="mt-10 grid animate-fade-up grid-cols-3 gap-4 border-t pt-6" style={{ animationDelay: '240ms' }}>
            {[
              ['PDF · DOCX · TXT', 'JD formats'],
              ['60 / 40', 'Skills / seniority'],
              ['CSV · JSON', 'Export'],
            ].map(([value, label]) => (
              <div key={label}>
                <dt className="text-xs text-muted-foreground">{label}</dt>
                <dd className="mt-1 text-sm font-semibold">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="animate-fade-up" style={{ animationDelay: '200ms' }}>
          <LiveDemo />
        </div>
      </div>
    </section>
  )
}

function SectionHeading({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <Reveal className="mx-auto mb-12 max-w-2xl text-center">
      <p className="mb-3 text-sm font-semibold text-primary">{eyebrow}</p>
      <h2 className="text-3xl font-semibold sm:text-4xl">{title}</h2>
      <p className="mt-4 text-lg leading-relaxed text-muted-foreground">{body}</p>
    </Reveal>
  )
}

const STEPS = [
  {
    icon: FileText,
    title: 'Parse the JD',
    body: 'Paste it or upload a PDF, DOCX or text file. TalentLens extracts the skills, technologies, seniority and domain, and you review them before anything runs.',
    visual: (
      <div className="flex flex-wrap gap-1.5">
        {['Go', 'Kubernetes', 'PostgreSQL', 'Senior'].map((s, i) => (
          <span
            key={s}
            className={cn(
              'rounded-full px-2.5 py-0.5 text-xs font-medium',
              i === 3 ? 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300' : 'bg-primary/10 text-primary',
            )}
          >
            {s}
          </span>
        ))}
      </div>
    ),
  },
  {
    icon: Radar,
    title: 'Source in the background',
    body: 'Requirements become search queries that run against GitHub and Stack Overflow while you get on with your day. Re-run any time; earlier runs stay available.',
    visual: (
      <div className="flex gap-2">
        {[
          { label: 'GitHub', icon: GitBranch },
          { label: 'Stack Overflow', icon: Hash },
        ].map(({ label, icon: Icon }) => (
          <span key={label} className="inline-flex items-center gap-1.5 rounded-lg border bg-background px-2.5 py-1 text-xs font-medium">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
            </span>
            <Icon className="h-3 w-3" />
            {label}
          </span>
        ))}
      </div>
    ),
  },
  {
    icon: BarChart3,
    title: 'Rank, filter, export',
    body: 'Every profile gets a match score from skill overlap and seniority. Filter by skill, platform or minimum score, then export the shortlist to CSV or JSON.',
    visual: (
      <div className="space-y-1.5">
        {[88, 74, 52].map((w, i) => (
          <div key={w} className="flex items-center gap-2">
            <span className="w-6 font-mono text-[11px] text-muted-foreground">{w}</span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
              <span
                className={cn('block h-full rounded-full', i === 2 ? 'bg-amber-500' : 'bg-emerald-500')}
                style={{ width: `${w}%` }}
              />
            </span>
          </div>
        ))}
      </div>
    ),
  },
]

function HowItWorks() {
  return (
    <section id="how" className="scroll-mt-20 border-t bg-muted/30 py-24">
      <div className="container mx-auto">
        <SectionHeading
          eyebrow="How it works"
          title="From job description to shortlist in three steps"
          body="No boolean strings to write and no profiles to trawl through by hand. Start from the JD you already have."
        />
        <div className="relative grid gap-5 md:grid-cols-3">
          {/* Connector line behind the cards on wide screens */}
          <div className="absolute left-[16%] right-[16%] top-[2.65rem] hidden h-px bg-gradient-to-r from-transparent via-border to-transparent md:block" aria-hidden="true" />
          {STEPS.map(({ icon: Icon, title, body, visual }, i) => (
            <Reveal key={title} delayMs={i * 120}>
              <div className="group relative h-full rounded-2xl border bg-card p-6 transition-all duration-300 hover:-translate-y-1 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5">
                <div className="mb-5 flex items-center gap-3">
                  <span className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-brand-solid text-white shadow-lg shadow-primary/25 transition-transform duration-300 group-hover:scale-105">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="font-mono text-xs text-muted-foreground">0{i + 1}</span>
                </div>
                <h3 className="text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
                <div className="mt-5 rounded-xl border bg-muted/40 p-3">{visual}</div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Scoring() {
  return (
    <section id="scoring" className="scroll-mt-20 py-24">
      <div className="container mx-auto">
        <SectionHeading
          eyebrow="No black box"
          title="A score you can explain to a hiring manager"
          body="Every match is 60% skill overlap and 40% seniority fit. The same arithmetic runs on every candidate, so anyone looking at a profile sees how its number was reached."
        />
        <Reveal className="mx-auto max-w-5xl">
          <ScorePlayground />
        </Reveal>
      </div>
    </section>
  )
}

function Roles() {
  return (
    <section id="roles" className="scroll-mt-20 border-t bg-muted/30 py-24">
      <div className="container mx-auto">
        <SectionHeading
          eyebrow="Built for both sides of the table"
          title="Recruiters run the search. Hiring managers see the shortlist."
          body="Recruiters own their searches. Hiring managers ask for access and get a read-only view of the ranked candidates."
        />
        <Reveal className="mx-auto max-w-6xl">
          <RolesShowcase />
        </Reveal>
      </div>
    </section>
  )
}

function FinalCta() {
  return (
    <section className="py-24">
      <div className="container mx-auto">
        <Reveal>
          <div className="relative isolate overflow-hidden rounded-3xl bg-brand-solid px-6 py-16 text-center text-white shadow-2xl shadow-primary/20 sm:px-16">
            <div
              className="absolute inset-0 -z-10 opacity-30 [background-image:radial-gradient(rgba(255,255,255,0.5)_1px,transparent_1px)] [background-size:20px_20px] [mask-image:radial-gradient(ellipse_at_center,#000_20%,transparent_75%)]"
              aria-hidden="true"
            />
            <div className="absolute -right-24 -top-24 -z-10 h-72 w-72 animate-float rounded-full bg-white/20 blur-3xl" aria-hidden="true" />
            <h2 className="mx-auto max-w-2xl text-3xl font-semibold sm:text-4xl">Start with the job description you already have.</h2>
            <p className="mx-auto mt-4 max-w-xl text-lg text-white/80">
              Create an account, paste a JD, and see your first ranked shortlist.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Button asChild size="lg" className="group bg-white text-indigo-700 shadow-lg hover:bg-white/90">
                <Link to="/register">
                  Create an account
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white">
                <Link to="/login">Sign in</Link>
              </Button>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t py-10">
      <div className="container mx-auto flex flex-col items-center justify-between gap-4 px-4 text-sm text-muted-foreground sm:flex-row sm:px-8">
        <Logo className="text-base text-foreground" markClassName="h-6 w-6" />
        <p>Sources public developer profiles from GitHub and Stack Overflow.</p>
        <div className="flex gap-4">
          <Link to="/login" className="hover:text-foreground">Sign in</Link>
          <Link to="/register" className="hover:text-foreground">Create account</Link>
        </div>
      </div>
    </footer>
  )
}
