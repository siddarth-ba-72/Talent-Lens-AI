import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getRecruiters, createShareRequest, getRecruiterSearches } from '@/api/shareRequestApi'
import { useUiStore } from '@/stores/uiStore'
import { QUERY_KEYS } from '@/utils/constants'

const schema = z.object({
  recruiterUserId: z.string().min(1, 'Please select a recruiter'),
  searchId: z.string().min(1, 'Please select a search'),
  note: z.string().max(500).optional(),
})
type FormData = z.infer<typeof schema>

interface RequestAccessModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function RequestAccessModal({ open, onOpenChange }: RequestAccessModalProps) {
  const queryClient = useQueryClient()
  const { addToast } = useUiStore()
  const [selectedRecruiterId, setSelectedRecruiterId] = useState<string | null>(null)

  const { data: recruiters, isLoading: recruitersLoading } = useQuery({
    queryKey: [QUERY_KEYS.RECRUITERS],
    queryFn: getRecruiters,
    enabled: open,
  })

  const { data: recruiterSearches, isLoading: searchesLoading } = useQuery({
    queryKey: [QUERY_KEYS.RECRUITERS, selectedRecruiterId, 'searches'],
    queryFn: () => getRecruiterSearches(selectedRecruiterId!),
    enabled: !!selectedRecruiterId,
  })

  const { register, handleSubmit, formState: { errors }, setValue, reset, watch } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) => createShareRequest({ searchId: data.searchId, recruiterUserId: data.recruiterUserId, note: data.note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SHARE_REQUESTS] })
      addToast({ type: 'success', title: 'Request sent!', description: 'The recruiter will be notified.' })
      reset()
      setSelectedRecruiterId(null)
      onOpenChange(false)
    },
    onError: () => addToast({ type: 'error', title: 'Failed to send request' }),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Request Search Access</DialogTitle>
          <DialogDescription>
            Ask a recruiter to share one of their searches with you.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4 mt-2">
          <div className="space-y-2">
            <Label>Recruiter</Label>
            <Select onValueChange={(v) => {
                setValue('recruiterUserId', v, { shouldValidate: true })
                setValue('searchId', '', { shouldValidate: false })
                setSelectedRecruiterId(v)
              }}>
              <SelectTrigger>
                <SelectValue placeholder={recruitersLoading ? 'Loading…' : 'Select recruiter'} />
              </SelectTrigger>
              <SelectContent>
                {recruiters?.map((r) => (
                  <SelectItem key={r.id} value={r.id}>{r.name} ({r.email})</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.recruiterUserId && <p className="text-xs text-destructive">{errors.recruiterUserId.message}</p>}
          </div>

          <div className="space-y-2">
            <Label>Search</Label>
            <Select onValueChange={(v) => setValue('searchId', v, { shouldValidate: true })} disabled={!selectedRecruiterId}>
              <SelectTrigger>
                <SelectValue placeholder={
                  !selectedRecruiterId ? 'Select a recruiter first' :
                  searchesLoading ? 'Loading…' : 'Select a search'
                } />
              </SelectTrigger>
              <SelectContent>
                {recruiterSearches?.map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.searchId && <p className="text-xs text-destructive">{errors.searchId.message}</p>}
          </div>

          <div className="space-y-2">
            <Label>Note (optional)</Label>
            <Textarea
              {...register('note')}
              placeholder="Add a message to the recruiter…"
              className="resize-none"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => { setSelectedRecruiterId(null); reset(); onOpenChange(false) }}>Cancel</Button>
            <Button type="submit" loading={mutation.isPending} disabled={mutation.isPending}>
              Send Request
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
