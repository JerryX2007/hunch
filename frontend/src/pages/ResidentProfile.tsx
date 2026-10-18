import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { AlertStatus, CaseMatch, Finding, ResidentOverview } from '../api/types'
import { StatusBadge, TierBadge } from '../components/Badges'
import { fmtDate } from '../components/format'

const pct = (x: number) => `${Math.round(x * 100)}%`
const signal = (s: string) => s.replace('toileting.', '').replace('.', ' (') + (s.split('.').length > 2 ? ')' : '')

export default function ResidentProfile() {
  const { residentId = '' } = useParams()
  const [data, setData] = useState<ResidentOverview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    api.resident(residentId).then(setData).catch((e: Error) => setError(e.message))
  }, [residentId])

  useEffect(load, [load])

  async function review(status: AlertStatus) {
    if (!data?.alert) return
    setSaving(true)
    try {
      await api.setAlertStatus(data.alert.id, status)
      load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  if (error) return <div className="rounded-md bg-red-50 p-3 text-sm text-red-800">{error}</div>
  if (!data) return <p className="text-slate-500">Loading…</p>

  const { resident, check, alert, similar, notes } = data
  const story = alert?.explanation?.narrative
  const triggers = check?.findings.filter((f) => f.persisting || f.urgent) ?? []
  const onceOnly = check?.findings.filter((f) => !f.persisting && !f.urgent) ?? []

  return (
    <div className="space-y-6">
      <Link to="/nurse" className="text-sm text-blue-700 hover:underline">
        ← All residents
      </Link>

      {/* Header */}
      <section className="rounded-lg border bg-white p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">{resident.display_name}</h1>
          {check && <TierBadge tier={check.tier} />}
          {alert && <StatusBadge status={alert.status} />}
        </div>
        {check?.alert && <p className="mt-1 text-lg">{check.title}</p>}
        {check && (
          <p className="mt-1 text-sm text-slate-600">
            Compared {check.window.recent_start} to {check.window.recent_end} with {check.baseline_days} days of usual
            history ({check.window.baseline_start ?? '—'} to {check.window.baseline_end ?? '—'}).
          </p>
        )}

        {alert && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-slate-700">Your review:</span>
            {(
              [
                ['reviewed', 'Reviewed'],
                ['needs_assessment', 'Needs further assessment'],
                ['dismissed', 'Not useful'],
              ] as [AlertStatus, string][]
            ).map(([s, label]) => (
              <button
                key={s}
                disabled={saving || alert.status === s}
                onClick={() => review(s)}
                className={`rounded-md border px-3 py-1.5 text-sm ${alert.status === s ? 'border-slate-900 bg-slate-900 text-white' : 'bg-white hover:bg-slate-50'}`}
              >
                {label}
              </button>
            ))}
            {alert.status !== 'open' && (
              <button disabled={saving} onClick={() => review('open')} className="text-sm text-slate-500 underline">
                Reset
              </button>
            )}
            <span className="w-full text-xs text-slate-500">
              Records what you did with this finding. It is not a diagnosis.
            </span>
          </div>
        )}
        {check?.alert && !alert && (
          <p className="mt-3 text-sm text-amber-700">Not saved as an alert yet. Use "Re-run check" on the dashboard.</p>
        )}
      </section>

      {/* Summary */}
      {story && story.source !== 'none' && (
        <section className="rounded-lg border bg-white p-4">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">Summary</h2>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {story.source === 'llm' ? 'AI draft, checked against the notes' : 'Generated from the rules'}
            </span>
          </div>
          <p className="mt-2">{story.summary}</p>
          {story.uncertainties.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600">
              {story.uncertainties.map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* Why flagged */}
      {check && (
        <section className="rounded-lg border bg-white p-4">
          <h2 className="text-lg font-semibold">{check.alert ? 'Why this resident was flagged' : 'What the check found'}</h2>
          {triggers.length === 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {check.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
          <div className="mt-3 space-y-4">
            {triggers.map((f) => (
              <FindingCard key={f.match_key} f={f} />
            ))}
          </div>
          {onceOnly.length > 0 && triggers.length > 0 && (
            <details className="mt-4 text-sm">
              <summary className="cursor-pointer text-slate-600">Noted once (context, not a trigger): {onceOnly.length}</summary>
              <div className="mt-2 space-y-3">
                {onceOnly.map((f) => (
                  <FindingCard key={f.match_key} f={f} />
                ))}
              </div>
            </details>
          )}
          {check.ruled_out.length > 0 && (
            <p className="mt-3 text-sm text-slate-600">Mentioned but ruled out in the notes: {check.ruled_out.join(', ')}</p>
          )}
          <p className="mt-3 text-xs text-slate-500">
            These observations don't establish a cause. A qualified staff member should review the resident.
          </p>
        </section>
      )}

      {/* Similar cases */}
      {similar && similar.cases.length > 0 && (
        <section className="rounded-lg border-2 border-dashed border-slate-300 bg-slate-100/60 p-4">
          <h2 className="text-lg font-semibold">What happened in similar past cases</h2>
          <p className="text-sm text-slate-600">{similar.note} Similar observations can have different causes.</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {similar.outcomes.map((o) => (
              <span key={o.outcome_category ?? 'unknown'} className="rounded-full bg-white px-2.5 py-1 ring-1 ring-slate-200">
                {(o.outcome_category ?? 'unknown').replace(/_/g, ' ')} × {o.n}
              </span>
            ))}
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {similar.cases.map((c) => (
              <CaseCard key={c.historical_case_id} c={c} />
            ))}
          </div>
        </section>
      )}

      {/* Recent notes */}
      <section className="rounded-lg border bg-white p-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Last {notes.length} notes</h2>
          <Link to={`/psw?resident=${resident.id}`} className="ml-auto text-sm text-blue-700 hover:underline">
            + Log a note
          </Link>
        </div>
        <ul className="mt-2 divide-y">
          {notes.map((n) => (
            <li key={n.id} className="py-2 text-sm">
              <span className="mr-2 whitespace-nowrap text-slate-500">
                {fmtDate(n.recorded_at)} · {n.author_role ?? 'staff'}
              </span>
              {n.note_text}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function FindingCard({ f }: { f: Finding }) {
  return (
    <div className={`rounded-md border-l-4 p-3 ${f.urgent ? 'border-red-600 bg-red-50' : f.persisting ? 'border-amber-500 bg-amber-50/50' : 'border-slate-300 bg-slate-50'}`}>
      <p className="font-medium">{f.reason}</p>
      {f.persisting && (
        <p className="mt-1 text-xs text-slate-600">
          Usual: on {pct(f.baseline_rate)} of days · Recent: on {pct(f.recent_rate)} of days ({f.recent_days.join(', ')})
        </p>
      )}
      {f.evidence && f.evidence.length > 0 && (
        <ul className="mt-2 space-y-1 text-sm">
          {f.evidence.map((e, i) => (
            <li key={`${e.note_id}-${i}`} className="flex gap-2">
              <span className="whitespace-nowrap text-slate-500">
                {fmtDate(e.recorded_at)} · {e.author_role ?? 'staff'}
              </span>
              <span title={e.note_text}>"{e.phrase}"</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function CaseCard({ c }: { c: CaseMatch }) {
  return (
    <div className="rounded-md border bg-white p-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-semibold">{c.historical_case_id}</span>
        <span className="text-xs text-slate-500">match {Math.round(c.total_score * 100)}%</span>
        <span className="ml-auto text-xs text-slate-500">{c.duration_days} days</span>
      </div>
      <p className="mt-1 text-slate-700">{c.case_summary}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {c.shared_signals.map((s) => (
          <span key={s} className="rounded bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-800 ring-1 ring-emerald-200">
            {signal(s)}
          </span>
        ))}
      </div>
      {c.differences.length > 0 && (
        <ul className="mt-2 list-disc pl-5 text-xs text-slate-600">
          {c.differences.map((d) => (
            <li key={d.text}>{d.text}</li>
          ))}
        </ul>
      )}
      <p className="mt-2">
        <span className="font-medium">Documented outcome: </span>
        {c.documented_outcome}
      </p>
      <p className="mt-1 text-xs text-slate-500">Limitations: {c.limitations}</p>
    </div>
  )
}
