import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ResidentSummary, RunResult } from '../api/types'
import { TierBadge } from '../components/Badges'

// Quick phrases, worded so the note reader recognises them (backend/app/history/extract.py).
const QUICK = [
  'Ate less than usual.',
  'More tired than usual.',
  'Drinking less than usual.',
  'Needed more help walking.',
  'Seemed confused.',
  'Complained of pain.',
  'Declined the afternoon activity.',
  'No BM for 3 days.',
]

export default function Psw() {
  const [params] = useSearchParams()
  const [residents, setResidents] = useState<ResidentSummary[]>([])
  const [rid, setRid] = useState(params.get('resident') ?? '')
  const [text, setText] = useState('')
  const [role, setRole] = useState('PSW')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)

  useEffect(() => {
    api
      .residents()
      .then((r) => setResidents([...r].sort((a, b) => a.display_name.localeCompare(b.display_name))))
      .catch((e: Error) => setError(e.message))
  }, [])

  function addPhrase(p: string) {
    setText((t) => (t.trim() ? `${t.trim()} ${p}` : p))
  }

  async function submit() {
    if (!rid || text.trim().length < 3) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const r = await api.addNote(rid, text, role)
      setResult(r.result)
      setText('')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Log a care note</h1>
        <p className="text-sm text-slate-600">Noticed something different? Pick the resident and say what you saw.</p>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">1. Resident</h2>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
          {residents.map((r) => (
            <button
              key={r.id}
              onClick={() => setRid(r.id)}
              className={`rounded-lg border px-2 py-3 text-sm font-semibold ${rid === r.id ? 'border-slate-900 bg-slate-900 text-white' : 'bg-white hover:bg-slate-50'}`}
            >
              {r.display_name}
            </button>
          ))}
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">2. What did you notice?</h2>
        <div className="mb-2 flex flex-wrap gap-2">
          {QUICK.map((p) => (
            <button key={p} onClick={() => addPhrase(p)} className="rounded-full border bg-white px-3 py-1.5 text-sm hover:bg-slate-50">
              {p.replace(/\.$/, '')}
            </button>
          ))}
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="e.g. Ate about half of breakfast. Seemed more tired than usual."
          className="w-full rounded-lg border p-3"
        />
        <div className="mt-2 flex items-center gap-3">
          <label className="text-sm text-slate-600">
            Role{' '}
            <select value={role} onChange={(e) => setRole(e.target.value)} className="ml-1 rounded border px-2 py-1">
              <option>PSW</option>
              <option>RPN</option>
              <option>RN</option>
            </select>
          </label>
          <button
            onClick={submit}
            disabled={busy || !rid || text.trim().length < 3}
            className="ml-auto rounded-lg bg-slate-900 px-5 py-2.5 font-semibold text-white disabled:opacity-40"
          >
            {busy ? 'Saving…' : 'Save note'}
          </button>
        </div>
      </div>

      {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</div>}
      {result && (
        <div className="rounded-lg border bg-white p-4">
          <p className="font-medium">Saved. Thank you. Every note helps the nurse see the full picture.</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <span>{result.resident_id} is now:</span>
            <TierBadge tier={result.tier} />
            {result.title && <span>{result.title}</span>}
          </div>
          <Link to={`/nurse/residents/${result.resident_id}`} className="mt-2 inline-block text-sm text-blue-700 hover:underline">
            Open in nurse view →
          </Link>
        </div>
      )}
    </div>
  )
}
