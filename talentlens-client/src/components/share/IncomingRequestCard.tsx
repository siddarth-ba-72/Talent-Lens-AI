import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, XCircle, Clock, ExternalLink } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { approveShareRequest, rejectShareRequest } from '@/api/shareRequestApi'
import { useUiStore } from '@/stores/uiStore'
import { getInitials, formatRelativeTime } from '@/utils/formatters'
import { QUERY_KEYS } from '@/utils/constants'
import type { ShareRequest } from '@/types/shareRequest'
import { Link } from 'react-router-dom'

interface IncomingRequestCardProps {
  request: ShareRequest
}

export function IncomingRequestCard({ request }: IncomingRequestCardProps) {
  const queryClient = useQueryClient()
  const { addToast } = useUiStore()

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SHARE_REQUESTS] })
  }

  const approveMutation = useMutation({
    mutationFn: () => approveShareRequest(request.id),
    onSuccess: () => { invalidate(); addToast({ type: 'success', title: 'Request approved' }) },
    onError: () => addToast({ type: 'error', title: 'Failed to approve' }),
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectShareRequest(request.id),
    onSuccess: () => { invalidate(); addToast({ type: 'success', title: 'Request rejected' }) },
    onError: () => addToast({ type: 'error', title: 'Failed to reject' }),
  })

  const isPending = request.status === 'PENDING'
  const isLoading = approveMutation.isPending || rejectMutation.isPending

  return (
    <Card className={!isPending ? 'opacity-60' : ''}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Avatar className="h-9 w-9 shrink-0">
            <AvatarFallback className="text-xs bg-primary/10 text-primary">
              {getInitials(request.requesterName ?? request.requesterUserId)}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium text-sm">{request.requesterName ?? request.requesterUserId}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  requesting access to{' '}
                  <Link to={`/searches/${request.searchId}`} className="text-primary hover:underline">
                    {request.searchTitle ?? request.searchId}
                  </Link>
                </p>
                {request.note && (
                  <p className="mt-1.5 text-xs text-muted-foreground italic">"{request.note}"</p>
                )}
              </div>
              <span className="text-xs text-muted-foreground shrink-0">{formatRelativeTime(request.requestedAt)}</span>
            </div>

            <div className="mt-3 flex items-center gap-2">
              {isPending ? (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5 h-7 text-xs text-emerald-600 border-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/20"
                    onClick={() => approveMutation.mutate()}
                    disabled={isLoading}
                    loading={approveMutation.isPending}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="gap-1.5 h-7 text-xs text-red-600 border-red-300 hover:bg-red-50 dark:hover:bg-red-900/20"
                    onClick={() => rejectMutation.mutate()}
                    disabled={isLoading}
                    loading={rejectMutation.isPending}
                  >
                    <XCircle className="h-3.5 w-3.5" /> Reject
                  </Button>
                </>
              ) : (
                <span className={`flex items-center gap-1.5 text-xs font-medium ${request.status === 'APPROVED' ? 'text-emerald-600' : 'text-red-500'}`}>
                  {request.status === 'APPROVED' ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
                  {request.status === 'APPROVED' ? 'Approved' : 'Rejected'}
                  {request.resolvedAt && <span className="text-muted-foreground font-normal">· {formatRelativeTime(request.resolvedAt)}</span>}
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
