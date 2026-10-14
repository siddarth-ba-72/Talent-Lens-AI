import type { Platform } from '@/types/search'

// Mirrors talentlens-ai/app/services/scoring_service.py so the landing page shows the
// same arithmetic the service uses. Keep the two in step.

export type Level = 'Junior' | 'Mid' | 'Senior' | 'Lead' | 'Not stated'

export const LEVELS: Level[] = ['Junior', 'Mid', 'Senior', 'Lead', 'Not stated']

const LEVEL_RANK: Record<Level, number> = { Junior: 1, Mid: 2, Senior: 3, Lead: 4, 'Not stated': 0 }

const normalize = (value: string) => value.trim().toLowerCase().split(/\s+/).join(' ')

/** Python's round(): halves go to the even neighbour. */
function roundHalfEven(value: number): number {
  const rounded = Math.round(value)
  return Math.abs(value % 1) === 0.5 && rounded % 2 !== 0 ? rounded - 1 : rounded
}

export function skillMatch(jdSkills: string[], candidateSkills: string[]): number {
  const jd = new Set(jdSkills.map(normalize).filter(Boolean))
  if (jd.size === 0) return 0
  const candidate = new Set(candidateSkills.map(normalize))
  const overlap = [...jd].filter((skill) => candidate.has(skill)).length
  return roundHalfEven((overlap / jd.size) * 100)
}

export function experienceMatch(jdLevel: Level, candidateLevel: Level): number {
  const jd = LEVEL_RANK[jdLevel]
  const candidate = LEVEL_RANK[candidateLevel]
  if (jd === 0 || candidate === 0) return 50
  return [100, 70, 40][Math.abs(jd - candidate)] ?? 20
}

export function matchScore(skill: number, experience: number): number {
  return Math.max(0, Math.min(100, roundHalfEven(0.6 * skill + 0.4 * experience)))
}

// Sample roles for the interactive demo. All people below are made up.

export interface DemoCandidate {
  handle: string
  name: string
  source: Platform
  level: Level
  skills: string[]
  signal: string
}

export interface DemoRole {
  id: string
  label: string
  title: string
  level: Level
  /** JD text; `[term]` marks an extracted skill, `[shown|Skill]` when the wording differs. */
  jd: string
  candidates: DemoCandidate[]
}

export const DEMO_ROLES: DemoRole[] = [
  {
    id: 'backend',
    label: 'Backend',
    title: 'Senior Backend Engineer',
    level: 'Senior',
    jd: 'We need a senior backend engineer (6+ years) to scale our payments platform. You will design services in [Go] and [Python], run them on [Kubernetes], and own [PostgreSQL] performance. [Kafka] and [gRPC] experience is a plus.',
    candidates: [
      { handle: 'quietcompiler', name: 'Mara Okafor', source: 'GITHUB', level: 'Senior', skills: ['Go', 'Kubernetes', 'PostgreSQL', 'gRPC', 'Rust'], signal: '38 repos · mostly Go' },
      { handle: 'lsm-tree', name: 'Ilya Brandt', source: 'STACKOVERFLOW', level: 'Lead', skills: ['PostgreSQL', 'Kafka', 'Python', 'Java'], signal: 'Top answerer in [postgresql]' },
      { handle: 'packet-pilot', name: 'Ana Ruiz', source: 'GITHUB', level: 'Mid', skills: ['Go', 'Python', 'Kafka', 'Kubernetes', 'gRPC', 'PostgreSQL'], signal: '21 repos · Go, Python' },
      { handle: 'devon-k', name: 'Devon Kerr', source: 'GITHUB', level: 'Junior', skills: ['Python', 'Django', 'PostgreSQL'], signal: '12 repos · Python' },
    ],
  },
  {
    id: 'ml',
    label: 'ML',
    title: 'ML Engineer',
    level: 'Mid',
    jd: 'Mid-level ML engineer to ship ranking models to production. Strong [Python] and [PyTorch], feature pipelines in [Spark], model serving with [FastAPI], experiment tracking in [MLflow], and solid [SQL].',
    candidates: [
      { handle: 'gradient-garden', name: 'Priya Nair', source: 'GITHUB', level: 'Mid', skills: ['Python', 'PyTorch', 'FastAPI', 'MLflow', 'Docker'], signal: '27 repos · Python, Jupyter' },
      { handle: 'tensor-tom', name: 'Tomás Lindqvist', source: 'STACKOVERFLOW', level: 'Senior', skills: ['Python', 'PyTorch', 'Spark', 'SQL', 'MLflow', 'FastAPI'], signal: 'Top answerer in [pytorch]' },
      { handle: 'nb-runner', name: 'Hana Sato', source: 'GITHUB', level: 'Junior', skills: ['Python', 'PyTorch', 'SQL'], signal: '9 repos · Jupyter' },
      { handle: 'etl-otter', name: 'Sam Achebe', source: 'STACKOVERFLOW', level: 'Mid', skills: ['Spark', 'SQL', 'Scala'], signal: 'Active in [apache-spark]' },
    ],
  },
  {
    id: 'frontend',
    label: 'Frontend',
    title: 'Lead Frontend Engineer',
    level: 'Lead',
    jd: 'Lead frontend engineer to own our design system. Deep [React] and [TypeScript], a real commitment to [accessibility|Accessibility], end-to-end testing with [Playwright], and [Next.js]. [GraphQL] is nice to have.',
    candidates: [
      { handle: 'aria-live', name: 'Jo Whitfield', source: 'GITHUB', level: 'Lead', skills: ['React', 'TypeScript', 'Accessibility', 'Playwright', 'Storybook'], signal: '44 repos · TypeScript' },
      { handle: 'hydration-err', name: 'Leo Marchetti', source: 'STACKOVERFLOW', level: 'Senior', skills: ['React', 'Next.js', 'TypeScript', 'GraphQL'], signal: 'Top answerer in [next.js]' },
      { handle: 'pixelpusher', name: 'Rina Gupta', source: 'GITHUB', level: 'Mid', skills: ['React', 'CSS', 'Figma', 'TypeScript'], signal: '19 repos · TypeScript, CSS' },
      { handle: 'vue-and-me', name: 'Chris Novak', source: 'GITHUB', level: 'Lead', skills: ['Vue', 'TypeScript', 'Accessibility'], signal: '31 repos · Vue' },
    ],
  },
]

/** `order` is the skill's position among the JD's skills, in reading order. */
export type JdSegment = { text: string; skill?: string; order?: number }

/** Splits demo JD markup into plain text and highlighted skill segments. */
export function parseJd(jd: string): JdSegment[] {
  const segments: JdSegment[] = []
  const pattern = /\[([^\]|]+)(?:\|([^\]]+))?\]/g
  let last = 0
  for (const match of jd.matchAll(pattern)) {
    if (match.index > last) segments.push({ text: jd.slice(last, match.index) })
    segments.push({ text: match[1], skill: match[2] ?? match[1], order: segments.filter((x) => x.skill).length })
    last = match.index + match[0].length
  }
  if (last < jd.length) segments.push({ text: jd.slice(last) })
  return segments
}

export function jdSkills(role: DemoRole): string[] {
  return parseJd(role.jd).flatMap((segment) => (segment.skill ? [segment.skill] : []))
}

export interface RankedCandidate extends DemoCandidate {
  skill: number
  experience: number
  score: number
  matched: string[]
  missing: string[]
}

export function rankCandidates(role: DemoRole): RankedCandidate[] {
  const skills = jdSkills(role)
  return role.candidates
    .map((candidate) => {
      const skill = skillMatch(skills, candidate.skills)
      const experience = experienceMatch(role.level, candidate.level)
      const owned = new Set(candidate.skills.map(normalize))
      return {
        ...candidate,
        skill,
        experience,
        score: matchScore(skill, experience),
        matched: skills.filter((s) => owned.has(normalize(s))),
        missing: skills.filter((s) => !owned.has(normalize(s))),
      }
    })
    .sort((a, b) => b.score - a.score)
}
