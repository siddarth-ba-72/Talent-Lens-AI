import { Link, NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, LogOut, Share2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Logo } from '@/components/common/Logo'
import { ThemeToggle } from '@/components/common/ThemeToggle'
import { useAuthStore } from '@/stores/authStore'
import { cn } from '@/lib/utils'
import { getInitials } from '@/utils/formatters'
import { useShareRequests } from '@/hooks/useShareRequests'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
    isActive ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground',
  )

export function Navbar() {
  const { user, isAuthenticated, logout } = useAuthStore()
  const navigate = useNavigate()

  const { data: incoming } = useShareRequests('incoming', user?.role === 'RECRUITER')
  const pendingCount = incoming?.content?.filter((r) => r.status === 'PENDING').length ?? 0

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  if (!isAuthenticated) return null

  return (
    <header className="sticky top-0 z-40 border-b bg-background/75 backdrop-blur-lg supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between gap-4">
        <div className="flex items-center gap-6">
          <Link to="/dashboard" aria-label="TalentLens dashboard">
            <Logo />
          </Link>

          <nav className="flex items-center gap-1">
            <NavLink to="/dashboard" className={navLinkClass}>
              <LayoutDashboard className="h-4 w-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </NavLink>

            {user?.role === 'RECRUITER' && (
              <NavLink to="/share-requests" className={navLinkClass}>
                <Share2 className="h-4 w-4" />
                <span className="hidden sm:inline">Requests</span>
                {pendingCount > 0 && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[10px] font-bold text-primary-foreground">
                    {pendingCount}
                  </span>
                )}
              </NavLink>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          <div className="flex items-center gap-2.5 rounded-full border bg-card/60 py-1 pl-1 pr-1 sm:pr-3.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-solid text-[11px] font-semibold text-white">
              {getInitials(user?.name)}
            </span>
            <div className="hidden leading-tight sm:block">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-[11px] text-muted-foreground">{user?.role === 'RECRUITER' ? 'Recruiter' : 'Hiring manager'}</p>
            </div>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="Sign out">
                <LogOut className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Sign out</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </header>
  )
}
