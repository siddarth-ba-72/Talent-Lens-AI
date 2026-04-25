import { useState } from 'react'
import { Plus, Clock, CheckCircle2, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { IncomingRequestCard } from '@/components/share/IncomingRequestCard'
import { RequestAccessModal } from '@/components/share/RequestAccessModal'
import { Skeleton } from '@/components/ui/skeleton'
import { RoleGuard } from '@/components/layout/RoleGuard'
import { useShareRequests } from '@/hooks/useShareRequests'
import { useAuthStore } from '@/stores/authStore'
import { formatRelativeTime } from '@/utils/formatters'
import type { ShareRequest } from '@/types/shareRequest'
import { Link } from 'react-router-dom'

export default function ShareRequestsPage() {
  const { user } = useAuthStore()
  const [requestModalOpen, setRequestModalOpen] = useState(false)

  const isRecruiter = user?.role === 'RECRUITER'

  const { data: incoming, isLoading: incomingLoading } = useShareRequests('incoming')
  const { data: outgoing, isLoading: outgoingLoading } = useShareRequests('outgoing', !isRecruiter)

  return (
    <div className="container mx-auto py-8 space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Share Requests</h1>
          <p className="text-muted-foreground">
            {isRecruiter ? 'Manage requests from hiring managers' : 'Request and track access to searches'}
          </p>
        </div>
        <RoleGuard role="HIRING_MANAGER">
          <Button onClick={() => setRequestModalOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" /> Request Access
          </Button>
        </RoleGuard>
      </div>

      <Tabs defaultValue={isRecruiter ? 'incoming' : 'outgoing'}>
        <TabsList>
          <TabsTrigger value="incoming">
            Incoming
            {(incoming?.content?.filter((r) => r.status === 'PENDING').length ?? 0) > 0 && (
              <span className="ml-1.5 rounded-full bg-destructive text-destructive-foreground text-xs px-1.5 py-0.5 leading-none">
                {incoming?.content?.filter((r) => r.status === 'PENDING').length}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="outgoing">Outgoing</TabsTrigger>
        </TabsList>

        <TabsContent value="incoming" className="mt-4 space-y-3">
          {incomingLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24" />)
          ) : !incoming?.content?.length ? (
            <EmptyRequests message="No incoming requests yet." />
          ) : (
            incoming.content.map((req) => <IncomingRequestCard key={req.id} request={req} />)
          )}
        </TabsContent>

        <TabsContent value="outgoing" className="mt-4 space-y-3">
          {outgoingLoading ? (
            Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24" />)
          ) : !outgoing?.content?.length ? (
            <EmptyRequests message="You haven't sent any requests yet." />
          ) : (
            outgoing.content.map((req) => <OutgoingRequestCard key={req.id} request={req} />)
          )}
        </TabsContent>
      </Tabs>

      <RequestAccessModal open={requestModalOpen} onOpenChange={setRequestModalOpen} />
    </div>
  )
}

function OutgoingRequestCard({ request }: { request: ShareRequest }) {
  const statusConfig = {
    PENDING: { icon: <Clock className="h-4 w-4 text-amber-500" />, label: 'Pending', color: 'text-amber-600' },
    APPROVED: { icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />, label: 'Approved', color: 'text-emerald-600' },
    REJECTED: { icon: <XCircle className="h-4 w-4 text-red-500" />, label: 'Rejected', color: 'text-red-500' },
  }
  const config = statusConfig[request.status]

  return (
    <Card className={request.status !== 'PENDING' ? 'opacity-70' : ''}>
      <CardContent className="p-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">
            Access to{' '}
            <Link to={`/searches/${request.searchId}`} className="text-primary hover:underline">
              {request.searchTitle}
            </Link>
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            From <span className="font-medium">{request.ownerName}</span> · {formatRelativeTime(request.requestedAt)}
          </p>
          {request.note && (
            <p className="mt-1 text-xs text-muted-foreground italic">"{request.note}"</p>
          )}
        </div>
        <span className={`flex items-center gap-1.5 text-xs font-medium shrink-0 ${config.color}`}>
          {config.icon} {config.label}
        </span>
      </CardContent>
    </Card>
  )
}

function EmptyRequests({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="flex justify-center py-10">
        <p className="text-sm text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  )
}
