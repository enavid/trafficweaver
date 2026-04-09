import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { login as apiLogin, setToken, getToken } from '@/lib/api'

interface AuthCtx {
  isAuthenticated: boolean
  username: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthCtx>({
  isAuthenticated: false,
  username: null,
  login: async () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null)

  // Listen for forced logouts (401)
  useEffect(() => {
    const handler = () => {
      setUsername(null)
    }
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [])

  const login = useCallback(async (user: string, pass: string) => {
    const res = await apiLogin(user, pass)
    setToken(res.token)
    setUsername(res.username)
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUsername(null)
  }, [])

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!username, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
