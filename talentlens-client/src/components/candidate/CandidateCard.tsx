import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, Trash2, MapPin, Mail, GitBranch, Hash } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { MatchScoreBadge } from './MatchScoreBadge'
import { SkillTags } from './SkillTags'
import { deleteCandidate } from '@/api/candidateApi'
import { useUiStore } from '@/stores/uiStore'
import { getInitials } from '@/utils/formatters'
import { QUERY_KEYS } from '@/utils/constants'
import type { Candidate } from '@/types/candidate'
import { useState } from 'react'

interface CandidateCardProps {
  candidate: Candidate
  canDelete?: boolean
}

export function CandidateCard({ candidate, canDelete = false }: CandidateCardProps) {
  const queryClient = useQueryClient()
  const { addToast } = useUiStore()
  const [confirmOpen, setConfirmOpen] = useState(false)

  const deleteMutation = useMutation({
    mutationFn: () => deleteCandidate(candidate.searchId, candidate.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.CANDIDATES, candidate.searchId] })
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SEARCH, candidate.searchId] })
      addToast({ type: 'success', title: 'Candidate removed' })
    },
    onError: () => addToast({ type: 'error', title: 'Failed to remove candidate' }),
  })

  return (
    <>
      <Card className="group hover:shadow-md transition-all duration-200 hover:border-primary/20">
        <CardContent className="p-5">
          <div className="flex items-start gap-4">
            {/* Avatar + score */}
            <div className="flex flex-col items-center gap-2 shrink-0">
              <Avatar className="h-12 w-12 ring-2 ring-border">
                <AvatarImage src={candidate.avatarUrl} alt={candidate.name} />
                <AvatarFallback className="text-sm font-semibold bg-primary/10 text-primary">
                  {getInitials(candidate.name)}
                </AvatarFallback>
              </Avatar>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <MatchScoreBadge score={candidate.matchScore} size="sm" />
                  </div>
                </TooltipTrigger>
                <TooltipContent className="space-y-1 text-xs">
                  <p className="font-medium mb-1">Score Breakdown</p>
                  <p>Skills: {candidate.scoreBreakdown.skillMatch}</p>
                  <p>Experience: {candidate.scoreBreakdown.experienceMatch}</p>
                  <p>Overall: {candidate.scoreBreakdown.overallFit}</p>
                </TooltipContent>
              </Tooltip>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-base">{candidate.name}</h3>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                      candidate.source === 'GITHUB'
                        ? 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                        : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                    }`}>
                      {candidate.source === 'GITHUB'
                        ? <GitBranch className="h-3 w-3" />
                        : <Hash className="h-3 w-3" />}
                      {candidate.source === 'GITHUB' ? 'GitHub' : 'Stack Overflow'}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    {candidate.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3" />{candidate.location}
                      </span>
                    )}
                    {candidate.email && (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3" />{candidate.email}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <Button asChild variant="ghost" size="icon" className="h-7 w-7">
                    <a href={candidate.profileUrl} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                  {canDelete && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => setConfirmOpen(true)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              </div>

              {/* Skills */}
              {candidate.skills?.length > 0 && (
                <div className="mt-3">
                  <SkillTags skills={candidate.skills} max={6} />
                </div>
              )}

              {/* Experience */}
              {candidate.experience?.length > 0 && (
                <div className="mt-3 space-y-1">
                  {candidate.experience.slice(0, 2).map((exp, i) => (
                    <p key={i} className="text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">{exp.title}</span>
                      {exp.company && ` · ${exp.company}`}
                      {exp.duration && ` (${exp.duration})`}
                    </p>
                  ))}
                </div>
              )}

              {/* Education */}
              {candidate.education?.length > 0 && (
                <p className="mt-1.5 text-xs text-muted-foreground">
                  🎓 {candidate.education[0].degree}{candidate.education[0].institution && `, ${candidate.education[0].institution}`}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Remove Candidate"
        description={`Remove ${candidate.name} from this search? This cannot be undone.`}
        confirmLabel="Remove"
        destructive
        onConfirm={() => deleteMutation.mutateAsync()}
      />
    </>
  )
}
