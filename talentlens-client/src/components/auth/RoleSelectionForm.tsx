import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'
import { googleCompleteSignup } from '@/api/googleAuthApi'
import type { UserRole } from '@/types/auth'
import type { AxiosError } from 'axios'
import type { ApiError } from '@/types/common'

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
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-4">
      <div className="w-full max-w-md animate-fade-in">
        <Card className="shadow-xl border-border/50">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl">One more step</CardTitle>
            <CardDescription>
              Welcome{name ? `, ${name}` : ''}! Tell us how you'll use TalentLens to finish creating your account.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
                Signing up as <span className="font-medium text-foreground">{email}</span>
              </div>

              <div className="space-y-2">
                <Label>I am a</Label>
                <Select value={role} onValueChange={(v) => setRole(v as UserRole)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select your role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="RECRUITER">Recruiter</SelectItem>
                    <SelectItem value="HIRING_MANAGER">Hiring Manager</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {error && (
                <div className="rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              )}

              <Button type="submit" className="w-full" loading={submitting}>
                Finish sign-up
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
