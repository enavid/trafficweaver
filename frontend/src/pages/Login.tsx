import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { useTheme } from '@/hooks/useTheme'
import Button from '@/components/Button'
import Input from '@/components/Input'
import { Activity, Sun, Moon, AlertCircle } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const { theme, toggle } = useTheme()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
    } catch (err: any) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'var(--color-bg)' }}
    >
      {/* Theme toggle */}
      <button
        onClick={toggle}
        className="fixed top-4 right-4 p-2 rounded-lg transition-colors"
        style={{ color: 'var(--color-text-muted)', background: 'var(--color-surface)' }}
        data-testid="login-toggle-theme"
      >
        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <div
        className="w-full max-w-sm rounded-2xl p-8"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-14 h-14 rounded-xl flex items-center justify-center mb-4"
            style={{ background: 'var(--color-primary)' }}
          >
            <Activity size={28} style={{ color: 'var(--color-text-inverse)' }} />
          </div>
          <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>
            TrafficWeaver
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Sign in to continue
          </p>
        </div>

        {error && (
          <div
            className="flex items-center gap-2 px-3 py-2.5 rounded-lg mb-4 text-sm"
            style={{ background: 'rgba(248,113,113,0.1)', color: 'var(--color-error)' }}
          >
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Username"
            type="text"
            placeholder="admin"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            data-testid="input-username"
          />
          <Input
            label="Password"
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            data-testid="input-password"
          />
          <Button
            type="submit"
            className="w-full"
            size="lg"
            disabled={loading || !username || !password}
            data-testid="btn-login"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>

        <p className="text-xs text-center mt-6" style={{ color: 'var(--color-text-faint)' }}>
          Default credentials: admin / admin
        </p>
      </div>
    </div>
  )
}
