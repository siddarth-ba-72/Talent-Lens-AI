import { BookOpen, Boxes, Brain, GitBranch, GitMerge, Hash, Newspaper, Package, PenLine } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { Platform } from '@/types/search'

export type PlatformGroup = 'Code' | 'Community' | 'ML & data' | 'Packages' | 'Research'

export interface PlatformMeta {
  label: string
  description: string
  icon: LucideIcon
  group: PlatformGroup
  // Classes for the small source badge on candidate cards.
  badgeClass: string
}

const NEUTRAL_BADGE = 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'

export const PLATFORM_META: Record<Platform, PlatformMeta> = {
  GITHUB: {
    label: 'GitHub',
    description: 'Contributors to projects in your stack, and matching profiles',
    icon: GitBranch,
    group: 'Code',
    badgeClass: NEUTRAL_BADGE,
  },
  GITLAB: {
    label: 'GitLab',
    description: 'Members of active GitLab.com projects in your stack',
    icon: GitMerge,
    group: 'Code',
    badgeClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  },
  STACKOVERFLOW: {
    label: 'Stack Overflow',
    description: 'Top answerers in the JD’s tags',
    icon: Hash,
    group: 'Community',
    badgeClass: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  },
  HACKERNEWS: {
    label: 'Hacker News',
    description: 'People who posted in “Who wants to be hired?”',
    icon: Newspaper,
    group: 'Community',
    badgeClass: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  },
  DEVTO: {
    label: 'dev.to',
    description: 'Authors of well-received posts on the JD’s topics',
    icon: PenLine,
    group: 'Community',
    badgeClass: NEUTRAL_BADGE,
  },
  HUGGINGFACE: {
    label: 'Hugging Face',
    description: 'Authors of models in the JD’s ML stack',
    icon: Brain,
    group: 'ML & data',
    badgeClass: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  },
  NPM: {
    label: 'npm',
    description: 'Maintainers of widely used JavaScript packages',
    icon: Package,
    group: 'Packages',
    badgeClass: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  },
  CRATES: {
    label: 'crates.io',
    description: 'Owners of popular Rust crates',
    icon: Boxes,
    group: 'Packages',
    badgeClass: 'bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300',
  },
  OPENALEX: {
    label: 'Research papers',
    description: 'Authors of recent papers on the JD’s topics (OpenAlex)',
    icon: BookOpen,
    group: 'Research',
    badgeClass: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
  },
}

export const PLATFORM_GROUPS: PlatformGroup[] = ['Code', 'Community', 'ML & data', 'Packages', 'Research']

export const PLATFORMS = Object.keys(PLATFORM_META) as Platform[]

// Older runs may carry sources that are no longer offered.
export function getPlatformMeta(platform: string): PlatformMeta {
  return (
    PLATFORM_META[platform as Platform] ?? {
      label: platform,
      description: '',
      icon: Hash,
      group: 'Community',
      badgeClass: NEUTRAL_BADGE,
    }
  )
}
