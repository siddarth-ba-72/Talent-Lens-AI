import axiosInstance from './axiosInstance'
import type {
  GoogleCallbackRequest,
  GoogleCallbackResponse,
  GoogleCompleteSignupRequest,
  TokenResponse,
} from '@/types/auth'

export async function googleCallback(data: GoogleCallbackRequest): Promise<GoogleCallbackResponse> {
  const res = await axiosInstance.post<GoogleCallbackResponse>('/auth/google/callback', data)
  return res.data
}

export async function googleCompleteSignup(data: GoogleCompleteSignupRequest): Promise<TokenResponse> {
  const res = await axiosInstance.post<TokenResponse>('/auth/google/complete-signup', data)
  return res.data
}
