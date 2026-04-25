import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { PageLoader } from '@/components/common/LoadingSpinner'

export function PublicRoute() {
  const { isAuthenticated, isHydrated } = useAuthStore()

  if (!isHydrated) return <PageLoader />
  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  return <Outlet />
}
