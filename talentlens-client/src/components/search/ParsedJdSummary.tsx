import { useState } from 'react'
import { ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { ParsedJd } from '@/types/search'
import { cn } from '@/lib/utils'

interface ParsedJdSummaryProps {
  parsedJd: ParsedJd
  title?: string
  collapsible?: boolean
  defaultCollapsed?: boolean
  className?: string
}

function CollapsibleSection({ title, items, defaultOpen = true }: { title: string; items: string[]; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  if (!items?.length) return null
  return (
    <div className="space-y-2">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between text-sm font-medium text-foreground hover:text-primary transition-colors"
      >
        <span>{title} ({items.length})</span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <ul className="space-y-1 pl-3 border-l-2 border-border">
          {items.map((item, i) => (
            <li key={i} className="text-sm text-muted-foreground">{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ParsedJdSummary({ parsedJd, title, collapsible, defaultCollapsed = false, className }: ParsedJdSummaryProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)

  return (
    <Card className={cn('border-primary/20', className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="h-4 w-4 text-primary" />
            {title ?? 'Parsed Job Description'}
          </CardTitle>
          {collapsible && (
            <Button variant="ghost" size="sm" onClick={() => setCollapsed(!collapsed)} className="h-7 text-xs">
              {collapsed ? 'Expand' : 'Collapse'}
            </Button>
          )}
        </div>
        {parsedJd.summary && !collapsed && (
          <p className="text-sm text-muted-foreground leading-relaxed">{parsedJd.summary}</p>
        )}
      </CardHeader>

      {!collapsed && (
        <CardContent className="space-y-4 pt-0">
          {/* Meta badges */}
          <div className="flex flex-wrap gap-2">
            {parsedJd.experienceLevel && (
              <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 px-2.5 py-0.5 text-xs font-medium">
                {parsedJd.experienceLevel}
              </span>
            )}
            {parsedJd.domain && (
              <span className="inline-flex items-center rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 px-2.5 py-0.5 text-xs font-medium">
                {parsedJd.domain}
              </span>
            )}
          </div>

          {/* Skills */}
          {parsedJd.skills?.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Required Skills</p>
              <div className="flex flex-wrap gap-1.5">
                {parsedJd.skills.map((skill) => (
                  <Badge key={skill} variant="secondary" className="text-xs">
                    {skill}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Technologies */}
          {parsedJd.technologies?.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Technologies</p>
              <div className="flex flex-wrap gap-1.5">
                {parsedJd.technologies.map((tech) => (
                  <Badge key={tech} variant="outline" className="text-xs font-mono">
                    {tech}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <CollapsibleSection title="Responsibilities" items={parsedJd.responsibilities} defaultOpen={false} />
          <CollapsibleSection title="Qualifications" items={parsedJd.qualifications} defaultOpen={false} />
        </CardContent>
      )}
    </Card>
  )
}
