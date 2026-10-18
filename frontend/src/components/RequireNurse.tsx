import { useState, type FormEvent, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './authContext'
import { friendlyError } from './format'

/** The nurse screen: signed in, with a name on the account. */
export default function RequireNurse({ children }: { children: ReactNode }) {
  const { me } = useAuth()
  const location = useLocation()

  if (!me) return <div className="h-96 animate-pulse rounded-xl bg-paper/70" aria-label="Loading" />
  if (!me.signed_in) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  if (!me.profile) return <NameSetup email={me.user?.email ?? ''} />
  return <>{children}</>
}

function NameSetup({ email }: { email: string }) {
  const { saveProfile } = useAuth()
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await saveProfile(name.trim())
    } catch (err) {
      setError(friendlyError((err as Error).message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md py-6 sm:py-12">
      <form onSubmit={submit} className="rounded-xl border border-line bg-paper p-6 sm:p-8">
        <h1 className="text-2xl font-bold">What’s your name?</h1>
        <p className="mt-1 text-muted">It’s shown at the top of the screen while you’re signed in. ({email})</p>
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
        {error && <p className="mt-4 rounded-md bg-urgent-soft p-3 text-urgent">{error}</p>}
        <button
          type="submit"
          disabled={busy || !name.trim()}
          className="mt-6 w-full rounded-lg bg-care px-4 py-3 text-lg font-bold text-white hover:bg-care-dark disabled:opacity-40"
        >
          {busy ? 'Saving…' : 'Continue'}
        </button>
      </form>
    </div>
  )
}
