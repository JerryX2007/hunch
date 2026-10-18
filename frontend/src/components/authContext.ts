import { createContext, useContext } from 'react'
import type { Me } from '../api/types'

export interface AuthState {
  me: Me | null // null while the first check is running
  signIn: (email: string, password: string) => Promise<Me>
  signOut: () => Promise<void>
  saveProfile: (fullName: string) => Promise<void>
  recheck: () => Promise<void>
}

export const AuthCtx = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
