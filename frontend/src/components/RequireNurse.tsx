import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import type { StaffRole } from '../api/types'
import { useAuth } from './authContext'
import { friendlyError } from './format'

/** The nurse screen: signed in, with an RN / RPN / NP profile. */
export default function RequireNurse({ children }: { children: ReactNode }) {
  const { me, signOut } = useAuth()
  const location = useLocation()

  if (!me) return <div className="h-96 animate-pulse rounded-xl bg-paper/70" aria-label="Loading" />
  if (!me.signed_in) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  if (!me.profile) return <ProfileSetup email={me.user?.email ?? ''} />
  if (!me.is_nurse)
    return (
      <div className="mx-auto max-w-md py-12">
        <h1 className="text-2xl font-bold">This screen is for nurses</h1>
        <p className="mt-2 text-muted">
          You’re signed in as {me.profile.full_name} ({me.profile.role}). The resident screen is for RN, RPN and NP staff.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link to="/psw" className="rounded-lg bg-care px-4 py-2.5 font-bold text-white hover:bg-care-dark">
            Log a note
          </Link>
          <button onClick={signOut} className="rounded-lg border border-line bg-paper px-4 py-2.5 font-bold hover:border-care">
            Sign out
          </button>
        </div>
      </div>
    )
  return <>{children}</>
}

function ProfileSetup({ email }: { email: string }) {
  const { saveProfile } = useAuth()
  const [name, setName] = useState('')
  const [role, setRole] = useState<StaffRole>('RN')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await saveProfile(name.trim(), role)
    } catch (err) {
      setError(friendlyError((err as Error).message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md py-6 sm:py-12">
      <form onSubmit={submit} className="rounded-xl border border-line bg-paper p-6 sm:p-8">
        <h1 className="text-2xl font-bold">One more step</h1>
        <p className="mt-1 text-muted">Add your name and role. They’re shown on notes you write. ({email})</p>
        <label className="mt-6 block">
          <span className="font-bold">Your name</span>
          <input
            autoFocus
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-line px-3.5 py-3 text-base"
          />
        </label>
        <fieldset className="mt-4">
          <legend className="font-bold">Your role</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {(['RN', 'RPN', 'NP'] as StaffRole[]).map((r) => (
              <label
                key={r}
                className={`cursor-pointer rounded-md border px-4 py-2 font-bold ${role === r ? 'border-care bg-care text-white' : 'border-line bg-paper'}`}
              >
                <input type="radio" name="role" value={r} checked={role === r} onChange={() => setRole(r)} className="sr-only" />
                {r}
              </label>
            ))}
          </div>
        </fieldset>
        {error && <p className="mt-4 rounded-md bg-urgent-soft p-3 text-urgent">{error}</p>}
        <button
          type="submit"
          disabled={busy || !name.trim()}
          className="mt-6 w-full rounded-lg bg-care px-4 py-3 text-lg font-bold text-white hover:bg-care-dark disabled:opacity-40"
        >
          {busy ? 'Saving…' : 'Save and continue'}
        </button>
      </form>
    </div>
  )
}
