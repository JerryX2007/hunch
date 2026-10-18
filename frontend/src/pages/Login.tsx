import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../components/authContext'
import { friendlyError } from '../components/format'

export default function Login() {
  const { me, signIn } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = params.get('next')?.startsWith('/') ? params.get('next')! : '/nurse'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (me?.signed_in) return <Navigate to={next} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signIn(email, password)
      navigate(next, { replace: true })
    } catch (err) {
      setError(friendlyError((err as Error).message))
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md py-6 sm:py-12">
      <div className="rounded-xl border border-line bg-paper p-6 sm:p-8">
        <h1 className="text-2xl font-bold">Nurse sign-in</h1>
        <p className="mt-1 text-muted">Sign in with your own Hunch account to see residents and review alerts.</p>

        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <label className="block">
            <span className="font-bold">Email</span>
            <input
              type="email"
              autoComplete="username"
              autoFocus
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-line px-3.5 py-3 text-base"
            />
          </label>
          <label className="block">
            <span className="flex items-center font-bold">
              Password
              <button
                type="button"
                onClick={() => setShow(!show)}
                className="ml-auto text-sm font-bold text-care hover:underline"
                aria-pressed={show}
              >
                {show ? 'Hide' : 'Show'}
              </button>
            </span>
            <input
              type={show ? 'text' : 'password'}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-line px-3.5 py-3 text-base"
            />
          </label>

          {error && (
            <p className="rounded-md bg-urgent-soft p-3 text-urgent" role="alert">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !email || !password}
            className="w-full rounded-lg bg-care px-4 py-3 text-lg font-bold text-white hover:bg-care-dark disabled:opacity-40"
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-4 text-sm text-muted">Forgot your password? Ask whoever manages Hunch accounts on your unit.</p>

        {me?.demo_login && (
          <div className="mt-6 rounded-lg bg-ward p-4">
            <p className="font-bold">Running on demo data</p>
            <p className="mt-1 text-sm text-muted">Pick a nurse to fill in her or his details (password {me.demo_login.password}).</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {me.demo_login.nurses.map((n) => (
                <button
                  key={n.email}
                  type="button"
                  onClick={() => {
                    setEmail(n.email)
                    setPassword(me.demo_login!.password)
                  }}
                  className={`rounded-md border bg-paper px-3 py-1.5 text-sm font-bold hover:border-care hover:text-care ${email === n.email ? 'border-care text-care' : 'border-line'}`}
                >
                  {n.name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <p className="mt-5 text-center">
        Logging a note about a resident? <Link to="/psw" className="font-bold text-care underline">You don’t need to sign in.</Link>
      </p>
    </div>
  )
}
