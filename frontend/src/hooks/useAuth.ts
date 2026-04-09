import { useCallback } from 'react'
import { useAuthStore } from '@/store/auth'

export function useAuth() {
  const { token, user, setAuth, logout } = useAuthStore()
  const isAuthenticated = !!token

  const loginWithCode = useCallback(
    (code: string) => {
      return fetch(`/api/v1/auth/callback?code=${code}`)
        .then((r) => {
          if (!r.ok) throw new Error(`Auth failed: ${r.status}`)
          return r.json()
        })
        .then((data) => setAuth(data.access_token, data.user))
    },
    [setAuth],
  )

  return { token, user, isAuthenticated, loginWithCode, logout }
}
