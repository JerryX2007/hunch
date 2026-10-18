import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { api } from '../api/client'
import type { Health } from '../api/types'

export default function Layout() {
  const [health, setHealth] = useState<Health | null>(null)
  const [down, setDown] = useState(false)

  useEffect(() => {
    api
      .health()
      .then((h) => {
        setHealth(h)
        setDown(false)
      })
      .catch(() => setDown(true))
  }, [])

  const tab = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-2 text-base font-bold transition-colors ${isActive ? 'bg-white text-ink' : 'text-white/80 hover:bg-white/10 hover:text-white'}`

  const dbProblem = health && health.database !== 'ok'

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 bg-ink text-white">
        <div className="mx-auto flex max-w-7xl items-center gap-2 px-4 py-2.5 sm:gap-4">
          <Link to="/nurse" className="mr-1 flex items-baseline gap-2 rounded-md">
            <span className="text-xl font-bold tracking-tight">Hunch</span>
            <span className="hidden text-sm text-white/70 sm:inline">2 West</span>
          </Link>
          <nav className="flex gap-1" aria-label="Main">
            <NavLink to="/nurse" className={tab}>
              Residents
            </NavLink>
            <NavLink to="/psw" className={tab}>
              Log a note
            </NavLink>
          </nav>
          <div className="ml-auto hidden text-right text-sm text-white/70 md:block">
            {health && (
              <span title={health.database}>
                {health.mode === 'supabase' ? 'Live data' : 'Demo data'}
                {health.llm ? ', AI summaries on' : ''}
              </span>
            )}
          </div>
        </div>
      </header>

      {(down || dbProblem) && (
        <div className="bg-urgent px-4 py-2 text-center text-sm text-white" role="alert">
          {down
            ? 'Can’t reach the Hunch server. Start it with python run.py, then reload.'
            : `The database isn’t answering (${health?.database}). To present without it: python run.py --demo`}
        </div>
      )}

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-5">
        <Outlet />
      </main>

      <footer className="px-4 pb-5 text-center text-sm text-muted">
        Prototype for clinical review support. All residents and notes are fictional. Decisions stay with qualified staff.
      </footer>
    </div>
  )
}
