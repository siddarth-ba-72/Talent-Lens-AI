import axiosInstance from './axiosInstance'
import type { LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest, User } from '@/types/auth'

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const res = await axiosInstance.post<TokenResponse>('/auth/login', data)
  return res.data
}

export async function register(data: RegisterRequest): Promise<void> {
  await axiosInstance.post('/auth/register', data)
}

export async function refresh(data: RefreshTokenRequest): Promise<{ accessToken: string }> {
  const res = await axiosInstance.post<{ accessToken: string }>('/auth/refresh', data)
  return res.data
}

export async function getMe(): Promise<User> {
  const res = await axiosInstance.get<User>('/auth/me')
  return res.data
}
