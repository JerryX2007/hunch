import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { api } from '../api/client'
import type { Health } from '../api/types'

export default function Layout() {
  const [health, setHealth] = useState<Health | null>(null)
  const [down, setDown] = useState(false)

  useEffect(() => {
    api.health().then(setHealth).catch(() => setDown(true))
  }, [])

  const nav = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'}`

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="bg-slate-800 px-4 py-1 text-center text-xs text-slate-200">
        Prototype for clinical review support. All residents and notes are fictional.
      </div>
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <Link to="/" className="mr-2 text-lg font-bold tracking-tight">
            Hunch
          </Link>
          <nav className="flex gap-1">
            <NavLink to="/nurse" className={nav}>
              Nurse dashboard
            </NavLink>
            <NavLink to="/psw" className={nav}>
              Log a note
            </NavLink>
          </nav>
          <div className="ml-auto text-xs text-slate-500">
            {down && <span className="font-medium text-red-600">Backend not reachable. Is run.py running?</span>}
            {health && (
              <span title={health.database}>
                Data: {health.mode === 'supabase' ? 'Supabase' : 'demo (in memory)'}
                {health.database !== 'ok' && <span className="ml-1 font-medium text-red-600">· database error</span>}
                {' · '}Summaries: {health.llm ? 'Gemini, checked' : 'template'}
              </span>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl p-4">
        <Outlet />
      </main>
    </div>
  )
}
