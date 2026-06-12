import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { RoleSelectionForm } from '@/components/auth/RoleSelectionForm'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'
import { googleCallback } from '@/api/googleAuthApi'
import { OAUTH_SESSION_KEYS } from '@/utils/constants'
import type { AxiosError } from 'axios'
import type { ApiError } from '@/types/common'

interface PendingSignup {
  signupTicket: string
  email: string
  name: string | null
}

interface CallbackError {
  title: string
  detail: string
}

// Module-level guard. The OAuth callback should only execute once per full page load.
// A module-level flag survives React StrictMode's double-effect AND any component remount,
// which a useRef cannot reliably guarantee.
let callbackInFlight = false

export default function OAuthCallbackPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { addToast } = useUiStore()
  const { setTokens, setUser } = useAuthStore()
  const [pending, setPending] = useState<PendingSignup | null>(null)
  const [error, setError] = useState<CallbackError | null>(null)

  useEffect(() => {
    if (callbackInFlight) return
    callbackInFlight = true

    const code = params.get('code')
    const state = params.get('state')
    const googleErr = params.get('error')

    const verifier = sessionStorage.getItem(OAUTH_SESSION_KEYS.PKCE_VERIFIER)
    const expectedState = sessionStorage.getItem(OAUTH_SESSION_KEYS.STATE)
    const nonce = sessionStorage.getItem(OAUTH_SESSION_KEYS.NONCE)
    sessionStorage.removeItem(OAUTH_SESSION_KEYS.PKCE_VERIFIER)
    sessionStorage.removeItem(OAUTH_SESSION_KEYS.STATE)
    sessionStorage.removeItem(OAUTH_SESSION_KEYS.NONCE)

    if (googleErr) {
      setError({ title: 'Google sign-in cancelled', detail: googleErr })
      return
    }

    if (!code) {
      setError({ title: 'Missing authorization code', detail: 'Google did not return an authorization code.' })
      return
    }
    if (!verifier || !nonce || !expectedState) {
      setError({
        title: 'OAuth session lost',
        detail: 'PKCE verifier, state, or nonce missing from sessionStorage. Start the sign-in flow again.',
      })
      return
    }
    if (state !== expectedState) {
      setError({ title: 'State mismatch', detail: 'The state parameter from Google does not match. Possible CSRF — start over.' })
      return
    }

    googleCallback({ code, codeVerifier: verifier, nonce })
      .then((res) => {
        if (res.needsRoleSelection && res.signupTicket && res.email) {
          setPending({ signupTicket: res.signupTicket, email: res.email, name: res.name })
          return
        }
        if (res.auth) {
          setTokens(res.auth.accessToken, res.auth.refreshToken)
          setUser(res.auth.user)
          addToast({ type: 'success', title: `Welcome back, ${res.auth.user.name}!` })
          navigate('/dashboard', { replace: true })
          return
        }
        setError({ title: 'Unexpected response', detail: 'Server returned a response we did not understand.' })
      })
      .catch((err: AxiosError<ApiError>) => {
        // Surface as much as we can so the failure is debuggable.
        console.error('[OAuth callback] backend error', {
          status: err.response?.status,
          data: err.response?.data,
          message: err.message,
        })
        const data = err.response?.data
        const detail = data?.message ?? err.message ?? 'Unknown error'
        const code = data?.error ?? (err.response?.status ? `HTTP ${err.response.status}` : 'NETWORK')
        setError({ title: `Sign-in failed (${code})`, detail })
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (pending) {
    return (
      <RoleSelectionForm
        signupTicket={pending.signupTicket}
        email={pending.email}
        name={pending.name}
        onComplete={() => navigate('/dashboard', { replace: true })}
      />
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-background to-destructive/5 p-4">
        <div className="w-full max-w-md animate-fade-in">
          <Card className="shadow-xl border-destructive/30">
            <CardHeader>
              <CardTitle className="text-xl text-destructive">{error.title}</CardTitle>
              <CardDescription>{error.detail}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                className="w-full"
                onClick={() => {
                  callbackInFlight = false
                  navigate('/login', { replace: true })
                }}
              >
                Back to login
              </Button>
              <p className="mt-3 text-center text-xs text-muted-foreground">
                Details logged to the browser console for debugging.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return <PageLoader />
}
