import { create } from 'zustand'
import { STORAGE_KEYS } from '@/utils/constants'
import type { User, LoginRequest, RegisterRequest } from '@/types/auth'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isHydrated: boolean

  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  login: (credentials: LoginRequest) => Promise<void>
  register: (data: RegisterRequest) => Promise<void>
  refresh: () => Promise<string>
  logout: () => void
  hydrateFromStorage: () => void
}

// Lazy import to avoid circular dependencies with axiosInstance
let authApiModule: typeof import('@/api/authApi') | null = null
const getAuthApi = async () => {
  if (!authApiModule) {
    authApiModule = await import('@/api/authApi')
  }
  return authApiModule
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isHydrated: false,

  setTokens: (accessToken, refreshToken) => {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, accessToken)
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, refreshToken)
    set({ accessToken, refreshToken })
  },

  setUser: (user) => set({ user, isAuthenticated: true }),

  login: async (credentials) => {
    const { login } = await getAuthApi()
    const data = await login(credentials)
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.accessToken)
    localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, data.refreshToken)
    set({
      user: data.user,
      accessToken: data.accessToken,
      refreshToken: data.refreshToken,
      isAuthenticated: true,
      isHydrated: true,
    })
  },

  register: async (data) => {
    const { register } = await getAuthApi()
    await register(data)
  },

  refresh: async () => {
    const { refreshToken } = get()
    if (!refreshToken) throw new Error('No refresh token')
    const { refresh } = await getAuthApi()
    const data = await refresh({ refreshToken })
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, data.accessToken)
    set({ accessToken: data.accessToken })
    return data.accessToken
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
  },

  hydrateFromStorage: () => {
    const accessToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
    const refreshToken = localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
    if (accessToken && refreshToken) {
      set({ accessToken, refreshToken })
      // Validate token by fetching user profile
      getAuthApi().then(({ getMe }) => {
        getMe()
          .then((user) => set({ user, isAuthenticated: true, isHydrated: true }))
          .catch(() => {
            localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
            localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
            set({ accessToken: null, refreshToken: null, isAuthenticated: false, isHydrated: true })
          })
      })
    } else {
      set({ isHydrated: true })
    }
  },
}))
