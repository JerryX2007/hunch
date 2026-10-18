import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ResidentSummary, RunResult } from '../api/types'
import { TierBadge } from '../components/Badges'
import { friendlyError } from '../components/format'

// Each tap adds a sentence the note reader recognises (backend/app/history/extract.py).
const SIGNS: { label: string; text: string; urgent?: boolean }[] = [
  { label: 'Ate less', text: 'Ate less than usual.' },
  { label: 'Drank less', text: 'Drinking less than usual.' },
  { label: 'More tired', text: 'More tired than usual.' },
  { label: 'Confused', text: 'Seemed confused.' },
  { label: 'Needed more help walking', text: 'Needed more help walking.' },
  { label: 'In pain', text: 'Complained of pain.' },
  { label: 'Skipped activities', text: 'Declined the afternoon activity.' },
  { label: 'Poor night', text: 'Restless night.' },
  { label: 'No bowel movement 3+ days', text: 'No BM for 3 days.' },
  { label: 'Fell or found on floor', text: 'Found on floor.', urgent: true },
  { label: 'Short of breath', text: 'Short of breath.', urgent: true },
]

export default function Psw() {
  const [params, setParams] = useSearchParams()
  const [residents, setResidents] = useState<ResidentSummary[]>([])
  const [error, setError] = useState<string | null>(null)
  const rid = params.get('resident') ?? ''
  const [find, setFind] = useState('')
  const [picked, setPicked] = useState<string[]>([])
  const [extra, setExtra] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<{ name: string; run: RunResult | null; text: string } | null>(null)

  useEffect(() => {
    api
      .residents()
      .then((r) => setResidents([...r].sort((a, b) => a.display_name.localeCompare(b.display_name))))
      .catch((e: Error) => setError(friendlyError(e.message)))
  }, [])

  const resident = residents.find((r) => r.id === rid)
  const noteText = [...SIGNS.filter((s) => picked.includes(s.label)).map((s) => s.text), extra.trim()].filter(Boolean).join(' ')
  const urgentPicked = SIGNS.some((s) => s.urgent && picked.includes(s.label))
  const canSave = Boolean(resident) && noteText.length >= 3 && !busy
  const shownResidents = useMemo(
    () => residents.filter((r) => !find || `${r.id} ${r.display_name}`.toLowerCase().includes(find.toLowerCase())),
    [residents, find],
  )

  function choose(id: string) {
    setParams(id ? { resident: id } : {})
    setResult(null)
  }

  function toggle(label: string) {
    setPicked((p) => (p.includes(label) ? p.filter((x) => x !== label) : [...p, label]))
  }

  async function save() {
    if (!resident || !canSave) return
    setBusy(true)
    setError(null)
    try {
      const r = await api.addNote(resident.id, noteText, 'PSW')
      setResult({ name: resident.display_name, run: r.result, text: noteText })
      setPicked([])
      setExtra('')
    } catch (e) {
      setError(friendlyError((e as Error).message))
    } finally {
      setBusy(false)
    }
  }

  // ------------------------------------------------------------ saved
  if (result) {
    return (
      <div className="mx-auto max-w-xl space-y-5 py-4">
        <div className="rounded-xl border border-line bg-paper p-6">
          <p className="text-2xl font-bold">Saved for {result.name}. Thank you.</p>
          <p className="mt-2 text-muted">“{result.text}”</p>
          <p className="mt-4">The nurse sees it now. Every note helps spot changes early.</p>
          {result.run && result.run.tier !== 'quiet' && (
            <p className="mt-3 flex flex-wrap items-center gap-2">
              {result.name} now shows as <TierBadge tier={result.run.tier} />
            </p>
          )}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <button onClick={() => setResult(null)} className="rounded-lg bg-care px-4 py-4 text-lg font-bold text-white hover:bg-care-dark">
            Another note for {result.name}
          </button>
          <button onClick={() => choose('')} className="rounded-lg border border-line bg-paper px-4 py-4 text-lg font-bold hover:border-care">
            Choose another resident
          </button>
        </div>
      </div>
    )
  }

  // ------------------------------------------------------------ form
  return (
    <div className="mx-auto max-w-2xl pb-28">
      <h1 className="text-2xl font-bold">Log a note</h1>
      <p className="text-muted">Noticed something different? Tap what you saw. It takes a few seconds.</p>
      {error && <p className="mt-3 rounded-md bg-urgent-soft p-3 text-urgent">{error}</p>}

      {/* step: who */}
      <section className="mt-6">
        <h2 className="text-lg font-bold">Who is it about?</h2>
        {resident ? (
          <div className="mt-2 flex items-center gap-3 rounded-xl border-2 border-care bg-paper px-4 py-3">
            <span className="text-2xl font-bold">{resident.display_name}</span>
            <button onClick={() => choose('')} className="ml-auto rounded-md px-3 py-2 font-bold text-care hover:bg-care-soft">
              Change
            </button>
          </div>
        ) : (
          <>
            {residents.length > 8 && (
              <input
                value={find}
                onChange={(e) => setFind(e.target.value)}
                placeholder="Find a resident"
                className="mt-2 w-full rounded-lg border border-line bg-paper px-3.5 py-3 text-base"
              />
            )}
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {shownResidents.map((r) => (
                <button
                  key={r.id}
                  onClick={() => choose(r.id)}
                  className="min-h-16 rounded-xl border border-line bg-paper px-3 py-4 text-lg font-bold hover:border-care active:bg-care-soft"
                >
                  {r.display_name}
                </button>
              ))}
            </div>
          </>
        )}
      </section>

      {/* step: what */}
      <section className={`mt-7 ${resident ? '' : 'pointer-events-none opacity-40'}`} aria-disabled={!resident}>
        <h2 className="text-lg font-bold">What did you notice?</h2>
        <p className="text-sm text-muted">Tap all that apply.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {SIGNS.map((s) => {
            const on = picked.includes(s.label)
            return (
              <button
                key={s.label}
                aria-pressed={on}
                onClick={() => toggle(s.label)}
                className={`min-h-12 rounded-full border-2 px-4 py-2 text-base font-bold transition-colors ${
                  on
                    ? s.urgent
                      ? 'border-urgent bg-urgent text-white'
                      : 'border-care bg-care text-white'
                    : s.urgent
                      ? 'border-urgent/40 bg-paper text-urgent'
                      : 'border-line bg-paper text-ink hover:border-care'
                }`}
              >
                {on ? '✓ ' : ''}
                {s.label}
              </button>
            )
          })}
        </div>
        {urgentPicked && (
          <p className="mt-3 rounded-lg bg-urgent-soft p-3 font-bold text-urgent" role="alert">
            Tell the nurse in person now as well. Don’t wait for the app.
          </p>
        )}

        <label className="mt-5 block">
          <span className="text-lg font-bold">Anything else?</span> <span className="text-sm text-muted">(optional, any language)</span>
          <textarea
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            rows={3}
            placeholder="e.g. Ate about half of breakfast. Seemed quieter than usual."
            className="mt-2 w-full rounded-lg border border-line bg-paper p-3 text-base"
          />
        </label>
      </section>

      {/* sticky save */}
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-paper/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <p className="min-w-0 flex-1 truncate text-sm text-muted">
            {!resident ? 'Pick a resident first.' : noteText ? `“${noteText}”` : 'Tap what you noticed, or write it.'}
          </p>
          <button
            onClick={save}
            disabled={!canSave}
            className="shrink-0 rounded-lg bg-care px-6 py-3 text-lg font-bold text-white hover:bg-care-dark disabled:opacity-40"
          >
            {busy ? 'Saving…' : 'Save note'}
          </button>
        </div>
      </div>
      <p className="mt-6 text-sm text-muted">
        Nurses: see everyone on the <Link to="/nurse" className="font-bold text-care underline">Residents</Link> screen.
      </p>
    </div>
  )
}
