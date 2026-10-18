import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { SIGNED_OUT_EVENT, api } from '../api/client'
import type { Me, StaffRole } from '../api/types'
import { AuthCtx, type AuthState } from './authContext'

const SIGNED_OUT: Me = { signed_in: false, user: null, profile: null, is_nurse: false, demo_login: null }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null)

  const recheck = useCallback(async () => {
    try {
      setMe(await api.me())
    } catch {
      setMe(SIGNED_OUT) // server unreachable: the layout shows that banner
    }
  }, [])

  useEffect(() => {
    const first = window.setTimeout(recheck, 0)
    window.addEventListener(SIGNED_OUT_EVENT, recheck)
    return () => {
      window.clearTimeout(first)
      window.removeEventListener(SIGNED_OUT_EVENT, recheck)
    }
  }, [recheck])

  const value = useMemo<AuthState>(
    () => ({
      me,
      recheck,
      signIn: async (email, password) => {
        const next = await api.signIn(email, password)
        setMe(next)
        return next
      },
      signOut: async () => {
        try {
          await api.signOut()
        } finally {
          setMe((m) => ({ ...SIGNED_OUT, demo_login: m?.demo_login ?? null }))
        }
      },
      saveProfile: async (fullName: string, role: StaffRole) => {
        await api.saveProfile(fullName, role)
        await recheck()
      },
    }),
    [me, recheck],
  )

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}
