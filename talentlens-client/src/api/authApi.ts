import axiosInstance from './axiosInstance'
import type { LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest, User } from '@/types/auth'

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const res = await axiosInstance.post<TokenResponse>('/auth/login', data)
  return res.data
}

export async function register(data: RegisterRequest): Promise<TokenResponse> {
  const res = await axiosInstance.post<TokenResponse>('/auth/register', data)
  return res.data
}

export async function refresh(data: RefreshTokenRequest): Promise<{ accessToken: string }> {
  const res = await axiosInstance.post<{ accessToken: string }>('/auth/refresh', data)
  return res.data
}

export function logout(accessToken: string | null): Promise<unknown> {
  // Uses fetch rather than axiosInstance so it bypasses the 401 refresh interceptor,
  // and keepalive so it still completes if the caller navigates away right after.
  return fetch('/api/auth/logout', {
    method: 'POST',
    keepalive: true,
    credentials: 'same-origin',
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  })
}

export async function getMe(): Promise<User> {
  const res = await axiosInstance.get<User>('/auth/me')
  return res.data
}
