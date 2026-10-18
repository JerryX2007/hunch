import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { ResidentSummary } from '../api/types'
import { StatusBadge, TierBadge } from '../components/Badges'
import ResidentDetail from '../components/ResidentDetail'
import { useToast } from '../components/toastContext'
import { NEEDS_ATTENTION, TIER_LABEL, TIER_ORDER, TIER_STYLE, authorOf, fmtDate, friendlyError, niceLabel, plural } from '../components/format'

const REFRESH_MS = 30_000

function needsReview(r: ResidentSummary) {
  return NEEDS_ATTENTION.includes(r.tier) && (!r.alert || r.alert.status === 'open' || r.alert.status === 'needs_assessment')
}

export default function Nurse() {
  const { residentId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const search = useRef<HTMLInputElement>(null)

  const [rows, setRows] = useState<ResidentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [checking, setChecking] = useState(false)
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try {
      setRows(await api.residents())
      setUpdatedAt(new Date())
      setError(null)
    } catch (e) {
      setError(friendlyError((e as Error).message))
    }
  }, [])

  useEffect(() => {
    const first = window.setTimeout(load, 0)
    const t = window.setInterval(load, REFRESH_MS)
    return () => {
      window.clearTimeout(first)
      window.clearInterval(t)
    }
  }, [load])

  // "/" jumps to search, Escape clears it.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement
      if (e.key === '/' && !typing) {
        e.preventDefault()
        search.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  async function checkAgain() {
    setChecking(true)
    try {
      const r = await api.runCheck()
      await load()
      toast({ tone: 'ok', text: `Checked ${plural(r.residents.length, 'resident')}. ${plural(r.alerts, 'alert')} on the unit.` })
    } catch (e) {
      toast({ tone: 'error', text: friendlyError((e as Error).message) })
    } finally {
      setChecking(false)
    }
  }

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase()
    return (rows ?? []).filter((r) => !term || `${r.id} ${r.display_name}`.toLowerCase().includes(term))
  }, [rows, q])

  const toReview = filtered
    .filter(needsReview)
    .sort((a, b) => TIER_ORDER.indexOf(a.tier) - TIER_ORDER.indexOf(b.tier) || a.id.localeCompare(b.id))
  const handled = filtered.filter((r) => NEEDS_ATTENTION.includes(r.tier) && !needsReview(r))
  const others = filtered.filter((r) => !NEEDS_ATTENTION.includes(r.tier))

  const showDetailOnly = Boolean(residentId) // on small screens the detail replaces the list

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
      {/* ------------------------------------------------ list */}
      <section className={`min-w-0 ${showDetailOnly ? 'hidden lg:block' : ''}`} aria-label="Residents">
        <div className="flex items-end gap-3">
          <div>
            <h1 className="text-2xl font-bold">Who needs you</h1>
            <p className="text-muted">
              {rows ? `${plural(toReview.length, 'resident')} to review` : 'Loading residents…'}
            </p>
          </div>
          <button
            onClick={checkAgain}
            disabled={checking}
            className="ml-auto rounded-md border border-line bg-paper px-3 py-2 text-sm font-bold text-ink hover:border-care hover:text-care disabled:opacity-50"
          >
            {checking ? 'Checking…' : 'Check again'}
          </button>
        </div>

        <label className="mt-4 block">
          <span className="sr-only">Find a resident</span>
          <input
            ref={search}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && setQ('')}
            placeholder="Find a resident  ( / )"
            className="w-full rounded-lg border border-line bg-paper px-3.5 py-2.5 text-base placeholder:text-muted/80"
          />
        </label>

        {error && <p className="mt-3 rounded-md bg-urgent-soft p-3 text-urgent">{error}</p>}

        {rows && (
          <div className="mt-4 space-y-6">
            {toReview.length > 0 ? (
              <ul className="space-y-2">
                {toReview.map((r) => (
                  <ResidentRow key={r.id} r={r} selected={r.id === residentId} />
                ))}
              </ul>
            ) : (
              <p className="rounded-lg border border-dashed border-line bg-paper p-4 text-muted">
                {q ? `No one to review matches “${q}”.` : 'Nobody needs review right now. New notes are checked automatically.'}
              </p>
            )}

            {handled.length > 0 && (
              <div>
                <h2 className="mb-2 text-base font-bold text-muted">Already reviewed</h2>
                <ul className="space-y-2 opacity-80">
                  {handled.map((r) => (
                    <ResidentRow key={r.id} r={r} selected={r.id === residentId} compact />
                  ))}
                </ul>
              </div>
            )}

            {others.length > 0 && (
              <div>
                <h2 className="mb-2 text-base font-bold text-muted">Everyone else</h2>
                <ul className="flex flex-wrap gap-2">
                  {others.map((r) => (
                    <li key={r.id}>
                      <Link
                        to={`/nurse/residents/${r.id}`}
                        aria-current={r.id === residentId ? 'true' : undefined}
                        title={TIER_LABEL[r.tier]}
                        className={`flex items-center gap-2 rounded-full border bg-paper py-1.5 pl-2 pr-3 text-sm hover:border-care ${r.id === residentId ? 'border-care ring-2 ring-care/30' : 'border-line'}`}
                      >
                        <span className={`h-2.5 w-2.5 rounded-full ${TIER_STYLE[r.tier].bar}`} aria-hidden />
                        <span className="font-bold">{r.display_name}</span>
                        <span className="text-muted">{TIER_LABEL[r.tier].toLowerCase()}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {updatedAt && (
              <p className="text-sm text-muted">
                Updated {updatedAt.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })}. Refreshes every 30
                seconds.
              </p>
            )}
          </div>
        )}
      </section>

      {/* ------------------------------------------------ detail */}
      <section className={`min-w-0 ${showDetailOnly ? '' : 'hidden lg:block'}`} aria-label="Selected resident">
        {residentId ? (
          <>
            <button onClick={() => navigate('/nurse')} className="mb-3 rounded-md py-1 font-bold text-care lg:hidden">
              ‹ All residents
            </button>
            <ResidentDetail key={residentId} residentId={residentId} onChanged={load} />
          </>
        ) : (
          <EmptyDetail first={toReview[0]} />
        )}
      </section>
    </div>
  )
}

function ResidentRow({ r, selected, compact = false }: { r: ResidentSummary; selected: boolean; compact?: boolean }) {
  return (
    <li>
      <Link
        to={`/nurse/residents/${r.id}`}
        aria-current={selected ? 'true' : undefined}
        className={`relative block overflow-hidden rounded-lg border bg-paper py-3 pl-5 pr-4 transition-colors hover:border-care ${selected ? 'border-care ring-2 ring-care/30' : 'border-line'}`}
      >
        <span className={`absolute inset-y-0 left-0 w-1.5 ${TIER_STYLE[r.tier].bar}`} aria-hidden />
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-lg font-bold">{r.display_name}</span>
          <TierBadge tier={r.tier} />
          {r.alert && r.alert.status !== 'open' && <StatusBadge status={r.alert.status} />}
        </div>
        {r.changes.length > 0 && (
          <p className="mt-1 text-ink">
            {r.changes.map(niceLabel).join(', ')}
            {r.days ? <span className="text-muted">, over {plural(r.days, 'day')}</span> : null}
          </p>
        )}
        {!compact && r.last_note && (
          <p className="mt-1 truncate text-sm text-muted">
            <span className="text-ink/80">“{r.last_note.note_text}”</span> {authorOf(r.last_note)},{' '}
            {fmtDate(r.last_note.recorded_at)}
          </p>
        )}
      </Link>
    </li>
  )
}

function EmptyDetail({ first }: { first?: ResidentSummary }) {
  return (
    <div className="flex h-full min-h-72 flex-col items-start justify-center rounded-xl border border-dashed border-line bg-paper/60 p-8">
      <p className="text-xl font-bold">Pick a resident to see what changed and why.</p>
      <p className="mt-2 max-w-prose text-muted">
        Every flag is a comparison with that resident’s own usual pattern, with the notes that support it.
      </p>
      {first && (
        <Link
          to={`/nurse/residents/${first.id}`}
          className="mt-5 rounded-md bg-care px-4 py-2.5 font-bold text-white hover:bg-care-dark"
        >
          Start with {first.display_name}
        </Link>
      )}
    </div>
  )
}
