export type UserRole = 'RECRUITER' | 'HIRING_MANAGER'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  name: string
  email: string
  password: string
  role: UserRole
}

export interface TokenResponse {
  accessToken: string
  refreshToken: string
  user: User
}

export interface RefreshTokenRequest {
  refreshToken: string
}

export interface GoogleCallbackRequest {
  code: string
  codeVerifier: string
  nonce: string
  redirectUri: string
}

export interface GoogleCallbackResponse {
  needsRoleSelection: boolean
  auth: TokenResponse | null
  signupTicket: string | null
  email: string | null
  name: string | null
  picture: string | null
}

export interface GoogleCompleteSignupRequest {
  signupTicket: string
  role: UserRole
}
