import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { ResidentSummary, Tier } from '../api/types'
import { StatusBadge, TierBadge } from '../components/Badges'
import { TIER_LABEL, TIER_ORDER, fmtDate } from '../components/format'

export default function Nurse() {
  const [rows, setRows] = useState<ResidentSummary[] | null>(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [lastRun, setLastRun] = useState<string | null>(null)

  const load = useCallback(() => {
    api.residents().then(setRows).catch((e: Error) => setError(e.message))
  }, [])

  useEffect(load, [load])

  async function rerun() {
    setRunning(true)
    setError(null)
    try {
      const r = await api.runCheck()
      setLastRun(`Checked ${r.residents.length} residents: ${r.alerts} with alerts.`)
      load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  const counts = useMemo(() => {
    const c = Object.fromEntries(TIER_ORDER.map((t) => [t, 0])) as Record<Tier, number>
    rows?.forEach((r) => (c[r.tier] += 1))
    return c
  }, [rows])

  const shown = (rows ?? []).filter((r) => !q || `${r.id} ${r.display_name}`.toLowerCase().includes(q.toLowerCase()))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-2xl font-bold">Residents needing review</h1>
          <p className="text-sm text-slate-600">
            Each resident is compared with their own usual pattern. Most concerning first.
          </p>
        </div>
        <button
          onClick={rerun}
          disabled={running}
          className="ml-auto rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {running ? 'Checking…' : 'Re-run check'}
        </button>
      </div>

      {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {lastRun && <div className="text-sm text-slate-600">{lastRun}</div>}

      <div className="flex flex-wrap gap-2">
        {TIER_ORDER.map((t) => (
          <div key={t} className="flex items-center gap-2 rounded-lg border bg-white px-3 py-2">
            <TierBadge tier={t} />
            <span className="text-lg font-semibold">{counts[t]}</span>
          </div>
        ))}
      </div>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search by resident ID or name"
        className="w-full max-w-sm rounded-lg border px-3 py-2 text-sm"
      />

      {!rows && !error && <p className="text-slate-500">Loading…</p>}

      {rows && (
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Resident</th>
                <th className="px-3 py-2">Today</th>
                <th className="px-3 py-2">What changed</th>
                <th className="px-3 py-2">Review</th>
                <th className="px-3 py-2">Last note</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id} className="border-b last:border-0 hover:bg-slate-50">
                  <td className="px-3 py-2">
                    <Link to={`/nurse/residents/${r.id}`} className="font-semibold text-blue-700 hover:underline">
                      {r.display_name}
                    </Link>
                    {r.display_name !== r.id && <div className="text-xs text-slate-500">{r.id}</div>}
                  </td>
                  <td className="px-3 py-2">
                    <TierBadge tier={r.tier} />
                  </td>
                  <td className="max-w-md px-3 py-2 text-slate-700">
                    {r.title ?? (r.tier === 'quiet' ? '' : r.reasons[0] ?? TIER_LABEL[r.tier])}
                  </td>
                  <td className="px-3 py-2">{r.alert ? <StatusBadge status={r.alert.status} /> : <span className="text-slate-400">—</span>}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-500">{fmtDate(r.last_note_at)}</td>
                </tr>
              ))}
              {shown.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-slate-500">
                    No residents match "{q}".
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
