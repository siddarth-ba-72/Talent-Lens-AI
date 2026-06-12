import { Button } from '@/components/ui/button'
import { useUiStore } from '@/stores/uiStore'
import { OAUTH_SESSION_KEYS, GOOGLE_OAUTH } from '@/utils/constants'
import { generateVerifier, challengeFromVerifier } from '@/utils/pkce'

export function GoogleSignInButton({ label = 'Continue with Google' }: { label?: string }) {
  const { addToast } = useUiStore()

  const onClick = async () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) {
      addToast({
        type: 'error',
        title: 'Google sign-in unavailable',
        description: 'VITE_GOOGLE_CLIENT_ID is not configured.',
      })
      return
    }

    const verifier = generateVerifier()
    const challenge = await challengeFromVerifier(verifier)
    const state = crypto.randomUUID()
    const nonce = crypto.randomUUID()

    sessionStorage.setItem(OAUTH_SESSION_KEYS.PKCE_VERIFIER, verifier)
    sessionStorage.setItem(OAUTH_SESSION_KEYS.STATE, state)
    sessionStorage.setItem(OAUTH_SESSION_KEYS.NONCE, nonce)

    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: `${window.location.origin}${GOOGLE_OAUTH.CALLBACK_PATH}`,
      response_type: 'code',
      scope: GOOGLE_OAUTH.SCOPE,
      code_challenge: challenge,
      code_challenge_method: 'S256',
      state,
      nonce,
      access_type: 'online',
      prompt: 'select_account',
    })

    window.location.href = `${GOOGLE_OAUTH.AUTHORIZE_URL}?${params.toString()}`
  }

  return (
    <Button type="button" variant="outline" className="w-full" onClick={onClick}>
      <GoogleLogo className="mr-2 h-4 w-4" />
      {label}
    </Button>
  )
}

function GoogleLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.56c2.08-1.92 3.28-4.74 3.28-8.09Z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.76c-.99.66-2.25 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.85A11 11 0 0 0 12 23Z" />
      <path fill="#FBBC05" d="M5.84 14.11A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.45.34-2.11V7.04H2.18A11 11 0 0 0 1 12c0 1.77.42 3.45 1.18 4.96l3.66-2.85Z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.07.56 4.21 1.65l3.15-3.15C17.45 2.09 14.96 1 12 1A11 11 0 0 0 2.18 7.04l3.66 2.85C6.71 7.31 9.14 5.38 12 5.38Z" />
    </svg>
  )
}
