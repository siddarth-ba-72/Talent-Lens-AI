import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const axiosInstance = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// Track ongoing refresh to avoid concurrent refresh calls
let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

function processQueue(token: string) {
  refreshQueue.forEach((cb) => cb(token))
  refreshQueue = []
}

axiosInstance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('tl_access')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((token: string) => {
            if (original.headers) original.headers.Authorization = `Bearer ${token}`
            resolve(axiosInstance(original))
          })
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        const { useAuthStore } = await import('@/stores/authStore')
        const newToken = await useAuthStore.getState().refresh()
        processQueue(newToken)
        if (original.headers) original.headers.Authorization = `Bearer ${newToken}`
        return axiosInstance(original)
      } catch {
        processQueue('')
        const { useAuthStore } = await import('@/stores/authStore')
        useAuthStore.getState().logout()
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default axiosInstance
