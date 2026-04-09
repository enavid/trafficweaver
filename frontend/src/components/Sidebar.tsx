import { NavLink } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { useTheme } from '@/hooks/useTheme'
import {
  LayoutDashboard,
  Download,
  Globe,
  Settings,
  ScrollText,
  Sun,
  Moon,
  LogOut,
  Activity,
} from 'lucide-react'

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/download-sites', icon: Download, label: 'Download Sites' },
  { to: '/browsing-sites', icon: Globe, label: 'Browsing Sites' },
  { to: '/logs', icon: ScrollText, label: 'System Logs' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { logout } = useAuth()
  const { theme, toggle } = useTheme()

  return (
    <aside
      className="fixed left-0 top-0 bottom-0 w-64 flex flex-col z-50"
      style={{ background: 'var(--color-surface)', borderRight: '1px solid var(--color-border)' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center"
          style={{ background: 'var(--color-primary)' }}
        >
          <Activity size={20} style={{ color: 'var(--color-text-inverse)' }} />
        </div>
        <div>
          <h1 className="text-base font-semibold leading-tight" style={{ color: 'var(--color-text)' }}>
            TrafficWeaver
          </h1>
          <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>v1.1</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive ? 'nav-active' : 'nav-inactive'
              }`
            }
            style={({ isActive }) => ({
              background: isActive ? 'var(--color-primary-highlight)' : 'transparent',
              color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            })}
            onMouseEnter={(e) => {
              const el = e.currentTarget
              if (!el.classList.contains('nav-active')) {
                el.style.background = 'var(--color-surface-offset)'
              }
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget
              if (!el.classList.contains('nav-active')) {
                el.style.background = 'transparent'
              }
            }}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Bottom actions */}
      <div className="px-3 py-4 space-y-1" style={{ borderTop: '1px solid var(--color-border)' }}>
        <button
          onClick={toggle}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium w-full transition-colors"
          style={{ color: 'var(--color-text-muted)' }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-offset)' }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
          data-testid="toggle-theme"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
        </button>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium w-full transition-colors"
          style={{ color: 'var(--color-error)' }}
          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--color-surface-offset)' }}
          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent' }}
          data-testid="btn-logout"
        >
          <LogOut size={18} />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
