import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { PublicRoute } from '@/components/layout/PublicRoute'
import { Navbar } from '@/components/layout/Navbar'
import { PageLoader } from '@/components/common/LoadingSpinner'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { useAuthStore } from '@/stores/authStore'
import { useUiStore } from '@/stores/uiStore'

const LandingPage = lazy(() => import('@/pages/LandingPage'))
const LoginPage = lazy(() => import('@/pages/LoginPage'))
const RegisterPage = lazy(() => import('@/pages/RegisterPage'))
const OAuthCallbackPage = lazy(() => import('@/pages/OAuthCallbackPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const NewSearchPage = lazy(() => import('@/pages/NewSearchPage'))
const SearchDetailPage = lazy(() => import('@/pages/SearchDetailPage'))
const ShareRequestsPage = lazy(() => import('@/pages/ShareRequestsPage'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Cached API responses belong to the account that fetched them. Drop them whenever the
// signed-in user changes, or the next account in this tab is shown the previous one's data.
useAuthStore.subscribe((state, prev) => {
  if (state.user?.id !== prev.user?.id) queryClient.clear()
})

function AppLayout() {
  return (
    <div className="relative min-h-screen bg-background">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 -z-0 h-[420px] bg-[radial-gradient(ellipse_70%_60%_at_50%_-10%,hsl(var(--primary)/0.10),transparent_70%)]"
        aria-hidden="true"
      />
      <Navbar />
      <main className="relative">
        <ErrorBoundary>
          <Suspense fallback={
            <div className="flex items-center justify-center min-h-[60vh]">
              <PageLoader />
            </div>
          }>
            <Outlet />
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  )
}

function AppRoutes() {
  const { hydrateFromStorage } = useAuthStore()

  useEffect(() => {
    hydrateFromStorage()
  }, [hydrateFromStorage])

  return (
    <Suspense fallback={<PageLoader />}>
      {/* Outer Suspense handles auth/public pages; inner Suspense (in AppLayout) handles protected pages */}
      <Routes>
        <Route element={<PublicRoute />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/oauth/google/callback" element={<OAuthCallbackPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route element={<ProtectedRoute requiredRole="RECRUITER" />}>
              <Route path="/searches/new" element={<NewSearchPage />} />
            </Route>
            <Route path="/searches/:id" element={<SearchDetailPage />} />
            <Route path="/share-requests" element={<ShareRequestsPage />} />
          </Route>
        </Route>

        {/* Signed-in users reaching "/" are sent on to the dashboard by PublicRoute. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}

export default function App() {
  const { theme } = useUiStore()

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') root.classList.add('dark')
    else root.classList.remove('dark')
  }, [theme])

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <ErrorBoundary>
            <AppRoutes />
          </ErrorBoundary>
          <Toaster position="top-right" richColors closeButton />
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  )
}
