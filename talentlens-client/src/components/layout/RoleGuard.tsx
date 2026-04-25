import type { ReactNode } from 'react'
import { useAuthStore } from '@/stores/authStore'
import type { UserRole } from '@/types/auth'

interface RoleGuardProps {
  role: UserRole
  children: ReactNode
  fallback?: ReactNode
}

export function RoleGuard({ role, children, fallback = null }: RoleGuardProps) {
  const { user } = useAuthStore()
  if (user?.role !== role) return <>{fallback}</>
  return <>{children}</>
}
