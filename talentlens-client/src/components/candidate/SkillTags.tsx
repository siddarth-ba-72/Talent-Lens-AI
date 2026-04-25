import { useState } from 'react'
import { Badge } from '@/components/ui/badge'

interface SkillTagsProps {
  skills: string[]
  max?: number
}

export function SkillTags({ skills, max = 8 }: SkillTagsProps) {
  const [expanded, setExpanded] = useState(false)
  if (!skills?.length) return null

  const visible = expanded ? skills : skills.slice(0, max)
  const hidden = skills.length - max

  return (
    <div className="flex flex-wrap gap-1.5">
      {visible.map((skill) => (
        <Badge key={skill} variant="secondary" className="text-xs">
          {skill}
        </Badge>
      ))}
      {!expanded && hidden > 0 && (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-muted-foreground hover:text-primary transition-colors px-1.5"
        >
          +{hidden} more
        </button>
      )}
      {expanded && (
        <button
          onClick={() => setExpanded(false)}
          className="text-xs text-muted-foreground hover:text-primary transition-colors px-1.5"
        >
          show less
        </button>
      )}
    </div>
  )
}
