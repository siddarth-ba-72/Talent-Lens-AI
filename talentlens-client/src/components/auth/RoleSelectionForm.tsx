import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'
import { googleCompleteSignup } from '@/api/googleAuthApi'
import type { UserRole } from '@/types/auth'
import type { AxiosError } from 'axios'
import type { ApiError } from '@/types/common'
import { AuthLayout } from './AuthLayout'
import { RolePicker } from './RolePicker'

interface Props {
  signupTicket: string
  email: string
  name: string | null
  onComplete: () => void
}

export function RoleSelectionForm({ signupTicket, email, name, onComplete }: Props) {
  const [role, setRole] = useState<UserRole | ''>('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { setTokens, setUser } = useAuthStore()
  const { addToast } = useUiStore()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!role) {
      setError('Please select a role')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const res = await googleCompleteSignup({ signupTicket, role })
      setTokens(res.accessToken, res.refreshToken)
      setUser(res.user)
      addToast({ type: 'success', title: `Welcome, ${res.user.name}!` })
      onComplete()
    } catch (err) {
      const e = err as AxiosError<ApiError>
      const msg = e.response?.data?.message ?? 'Sign-up failed. Please try again.'
      setError(msg)
      addToast({ type: 'error', title: 'Sign-up failed', description: msg })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="One more step"
      description={<>Welcome{name ? `, ${name}` : ''}! Tell us how you'll use TalentLens to finish creating your account.</>}
    >
      <form onSubmit={onSubmit} className="space-y-5">
        <div className="rounded-lg border bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
          Signing up as <span className="font-medium text-foreground">{email}</span>
        </div>

        <div className="space-y-2">
          <Label>I am a</Label>
          <RolePicker value={role} onChange={(r) => { setRole(r); setError(null) }} />
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive animate-fade-in">
            {error}
          </div>
        )}

        <Button type="submit" className="w-full" loading={submitting}>
          Finish sign-up
        </Button>
      </form>
    </AuthLayout>
  )
}
