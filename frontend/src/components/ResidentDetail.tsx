import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { AlertStatus, CaseMatch, Finding, ResidentOverview } from '../api/types'
import { TierBadge } from './Badges'
import { useToast } from './toastContext'
import { STATUS_LABEL, TIER_HINT, TIER_STYLE, authorOf, capitalize, daysBetween, fmtDate, fmtDay, friendlyError, niceLabel, plural } from './format'

const REVIEW_OPTIONS: { status: AlertStatus; label: string; done: string }[] = [
  { status: 'reviewed', label: 'Reviewed', done: 'Marked as reviewed' },
  { status: 'needs_assessment', label: 'Needs assessment', done: 'Marked as needing assessment' },
  { status: 'dismissed', label: 'Not useful', done: 'Marked as not useful' },
]

export default function ResidentDetail({ residentId, onChanged }: { residentId: string; onChanged: () => void }) {
  const toast = useToast()
  const [data, setData] = useState<ResidentOverview | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setData(await api.resident(residentId))
      setError(null)
    } catch (e) {
      setError(friendlyError((e as Error).message))
    }
  }, [residentId])

  useEffect(() => {
    const first = window.setTimeout(load, 0)
    return () => window.clearTimeout(first)
  }, [load])

  async function setStatus(status: AlertStatus, quiet = false) {
    if (!data?.alert) return
    const before = data.alert.status
    setData({ ...data, alert: { ...data.alert, status } }) // show it straight away
    try {
      await api.setAlertStatus(data.alert.id, status)
      onChanged()
      if (!quiet) {
        const opt = REVIEW_OPTIONS.find((o) => o.status === status)
        toast({
          tone: 'ok',
          text: `${data.resident.display_name}: ${opt?.done ?? STATUS_LABEL[status]}.`,
          action: { label: 'Undo', run: () => setStatus(before, true) },
        })
      }
    } catch (e) {
      setData((d) => (d && d.alert ? { ...d, alert: { ...d.alert, status: before } } : d))
      toast({ tone: 'error', text: friendlyError((e as Error).message) })
    }
  }

  if (error) return <p className="rounded-md bg-urgent-soft p-4 text-urgent">{error}</p>
  if (!data) return <div className="h-96 animate-pulse rounded-xl bg-paper/70" aria-label="Loading" />

  const { resident, check, alert, similar, notes } = data
  const story = alert?.explanation?.narrative
  const triggers = check?.findings.filter((f) => f.persisting || f.urgent) ?? []
  const onceOnly = check?.findings.filter((f) => !f.persisting && !f.urgent) ?? []
  const recentDays = check?.window.recent_start && check.window.recent_end ? daysBetween(check.window.recent_start, check.window.recent_end) : []

  return (
    <article className="overflow-hidden rounded-xl border border-line bg-paper">
      {/* ---------------- header */}
      <header className="relative border-b border-line px-5 pb-4 pt-5 sm:px-6">
        {check && <span className={`absolute inset-x-0 top-0 h-1.5 ${TIER_STYLE[check.tier].bar}`} aria-hidden />}
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-3xl font-bold tracking-tight">
            {resident.display_name}
            {resident.display_name !== resident.id && (
              <span className="ml-3 align-middle text-lg font-normal text-muted">{resident.id}</span>
            )}
          </h2>
          {check && <TierBadge tier={check.tier} className="text-base" />}
        </div>
        {check && <p className="mt-1 text-muted">{TIER_HINT[check.tier]}</p>}

        {alert && (
          <div className="mt-4 rounded-lg bg-ward p-3">
            <p className="font-bold">What did you do about it?</p>
            <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Review">
              {REVIEW_OPTIONS.map((o) => {
                const on = alert.status === o.status
                return (
                  <button
                    key={o.status}
                    aria-pressed={on}
                    onClick={() => setStatus(on ? 'open' : o.status)}
                    className={`rounded-md border px-4 py-2 font-bold transition-colors ${on ? 'border-care bg-care text-white' : 'border-line bg-paper text-ink hover:border-care hover:text-care'}`}
                  >
                    {on ? `✓ ${o.label}` : o.label}
                  </button>
                )
              })}
            </div>
            <p className="mt-2 text-sm text-muted">This records your follow-up. It isn’t a diagnosis. Tap again to clear.</p>
          </div>
        )}
        {check?.alert && !alert && (
          <p className="mt-3 text-change">Not saved as an alert yet. Use “Check again” on the list.</p>
        )}
      </header>

      <div className="space-y-8 px-5 py-6 sm:px-6">
        {/* ---------------- what changed */}
        {check && (
          <section>
            <h3 className="text-xl font-bold">{triggers.length ? 'What changed' : 'Latest check'}</h3>
            {story && story.source === 'llm' ? (
              <p className="mt-2 max-w-prose text-lg">
                {story.summary} <span className="text-sm text-muted">(AI summary, checked against the notes)</span>
              </p>
            ) : check.urgent ? (
              <p className="mt-2 max-w-prose text-lg font-bold text-urgent">
                Serious event noted. Follow the home’s escalation procedure now; don’t wait for more notes.
              </p>
            ) : triggers.length > 0 ? (
              <p className="mt-2 max-w-prose text-lg">
                Different from {resident.display_name === resident.id ? resident.id : resident.display_name.split(' ')[0]}’s usual for {plural(check.duration_days, 'day')}:{' '}
                {triggers.map((f) => label(f).toLowerCase()).join(', ')}.
              </p>
            ) : (
              <ul className="mt-2 max-w-prose list-disc space-y-1 pl-5">
                {check.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}

            <div className="mt-4 space-y-3">
              {triggers.map((f) => (
                <FindingBlock key={f.match_key} f={f} days={recentDays} baselineDays={check.baseline_days} />
              ))}
            </div>

            {onceOnly.length > 0 && triggers.length > 0 && (
              <details className="mt-4 rounded-lg border border-line px-4 py-3">
                <summary className="cursor-pointer font-bold text-muted">
                  Noted only once ({onceOnly.length}), not counted as a change
                </summary>
                <div className="mt-3 space-y-3">
                  {onceOnly.map((f) => (
                    <FindingBlock key={f.match_key} f={f} days={recentDays} baselineDays={check.baseline_days} />
                  ))}
                </div>
              </details>
            )}
            {check.ruled_out.length > 0 && (
              <p className="mt-3 text-sm text-muted">Mentioned but ruled out in the notes: {check.ruled_out.map((r) => r.replace(' (ruled out in notes)', '')).join(', ')}.</p>
            )}
            {triggers.length > 0 && (
              <p className="mt-3 text-sm text-muted">
                These notes show a change; they don’t show the cause. Compared with {plural(check.baseline_days, 'day')} of earlier
                notes.
              </p>
            )}
          </section>
        )}

        {/* ---------------- similar cases */}
        {similar && similar.cases.length > 0 && <SimilarCases cases={similar.cases} outcomes={similar.outcomes} />}

        {/* ---------------- notes */}
        <NotesSection residentId={resident.id} name={resident.display_name} notes={notes} onSaved={() => { load(); onChanged() }} />
      </div>
    </article>
  )
}

function label(f: Finding) {
  return niceLabel(f.reason.split(':')[0].replace(/^URGENT - /, ''))
}

function FindingBlock({ f, days, baselineDays }: { f: Finding; days: string[]; baselineDays: number }) {
  const [open, setOpen] = useState(false)
  const ev = [...(f.evidence ?? [])].sort((a, b) => b.recorded_at.localeCompare(a.recorded_at)) // newest first
  const shown = open ? ev : ev.slice(0, 2)
  const noted = new Set(f.recent_days)
  const tone = f.urgent ? 'urgent' : f.persisting ? 'change' : 'quiet'
  const detail = f.reason.includes(':') ? f.reason.slice(f.reason.indexOf(':') + 1).trim() : f.reason

  return (
    <div className={`rounded-lg border p-4 ${tone === 'urgent' ? 'border-urgent/40 bg-urgent-soft' : 'border-line'}`}>
      <div className="flex flex-wrap items-start gap-x-5 gap-y-2">
        <div className="min-w-0 flex-1 basis-60">
          <p className="text-lg font-bold">{label(f)}</p>
          {!f.urgent && <p className="text-ink/90">{capitalize(detail)}</p>}
        </div>
        {days.length > 0 && !f.urgent && (
          <DayStrip days={days} noted={noted} usualRate={f.baseline_rate} baselineDays={baselineDays} tone={tone} />
        )}
      </div>
      {ev.length > 0 && (
        <ul className="mt-3 space-y-1.5 border-l-2 border-line pl-3">
          {shown.map((e, i) => (
            <li key={`${e.note_id}-${i}`} title={e.note_text}>
              <span className="text-ink">“{e.phrase}”</span>{' '}
              <span className="whitespace-nowrap text-sm text-muted">
                {authorOf(e)}, {fmtDate(e.recorded_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
      {ev.length > 2 && (
        <button onClick={() => setOpen(!open)} className="mt-2 text-sm font-bold text-care hover:underline">
          {open ? 'Show fewer notes' : `Show all ${ev.length} notes`}
        </button>
      )}
    </div>
  )
}

/** Usual vs the last few days, at a glance: one square per recent day, filled when it was noted. */
function DayStrip({
  days,
  noted,
  usualRate,
  baselineDays,
  tone,
}: {
  days: string[]
  noted: Set<string>
  usualRate: number
  baselineDays: number
  tone: 'urgent' | 'change' | 'quiet'
}) {
  const fill = tone === 'change' ? 'bg-change-bar' : tone === 'urgent' ? 'bg-urgent' : 'bg-muted'
  const usualDays = Math.round(usualRate * baselineDays)
  return (
    <figure className="shrink-0" aria-label={`Noted on ${noted.size} of the last ${days.length} days; usually ${usualDays} of ${baselineDays} days`}>
      <div className="flex items-end gap-3">
        <div className="text-center">
          <div className="flex h-7 w-12 items-center justify-center rounded border border-dashed border-line text-sm text-muted">
            {Math.round(usualRate * 100)}%
          </div>
          <figcaption className="mt-1 text-xs text-muted">usual</figcaption>
        </div>
        <div>
          <div className="flex gap-1">
            {days.map((d) => (
              <span
                key={d}
                title={`${fmtDay(d)}: ${noted.has(d) ? 'noted' : 'not noted'}`}
                className={`h-7 w-6 rounded ${noted.has(d) ? fill : 'border border-line bg-ward'}`}
              />
            ))}
          </div>
          <div className="mt-1 flex gap-1 text-xs text-muted" aria-hidden>
            {days.map((d) => (
              <span key={d} className="w-6 text-center">
                {fmtDay(d).slice(0, 2)}
              </span>
            ))}
          </div>
        </div>
      </div>
    </figure>
  )
}

function SimilarCases({ cases, outcomes }: { cases: CaseMatch[]; outcomes: { outcome_category: string | null; n: number }[] }) {
  const [all, setAll] = useState(false)
  const shown = all ? cases : cases.slice(0, 2)
  const spread = outcomes.map((o) => `${o.n} ${(o.outcome_category ?? 'unknown').replace(/_/g, ' ')}`).join(', ')
  return (
    <section className="rounded-xl bg-ward p-4 sm:p-5">
      <h3 className="text-xl font-bold">Past cases that looked like this</h3>
      <p className="mt-1 max-w-prose text-muted">
        From a fictional case library. Of {plural(cases.length, 'similar case')}, the documented causes were: {spread}. Similar notes
        can have different causes.
      </p>
      <div className="mt-4 grid gap-3 xl:grid-cols-2">
        {shown.map((c) => (
          <div key={c.historical_case_id} className="rounded-lg border border-line bg-paper p-4">
            <div className="flex items-baseline gap-2">
              <span className="font-bold">{c.historical_case_id}</span>
              <span className="text-sm text-muted">
                {Math.round(c.total_score * 100)}% match, {plural(c.duration_days, 'day')}
              </span>
            </div>
            <p className="mt-1">{c.case_summary}</p>
            <p className="mt-3 rounded-md bg-care-soft px-3 py-2">
              <span className="font-bold">What happened: </span>
              {c.documented_outcome}
            </p>
            {c.differences.length > 0 && (
              <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-muted">
                {c.differences.map((d) => (
                  <li key={d.text}>{d.text}</li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-sm text-muted">Missing from that record: {c.limitations}</p>
          </div>
        ))}
      </div>
      {cases.length > 2 && (
        <button onClick={() => setAll(!all)} className="mt-3 font-bold text-care hover:underline">
          {all ? 'Show fewer cases' : `Show ${cases.length - 2} more`}
        </button>
      )}
    </section>
  )
}

function NotesSection({
  residentId,
  name,
  notes,
  onSaved,
}: {
  residentId: string
  name: string
  notes: ResidentOverview['notes']
  onSaved: () => void
}) {
  const toast = useToast()
  const [text, setText] = useState('')
  const [saving, setSaving] = useState(false)

  async function save() {
    if (text.trim().length < 3) return
    setSaving(true)
    try {
      await api.addNote(residentId, text, 'Nurse')
      setText('')
      toast({ tone: 'ok', text: `Note saved for ${name} under your name. Re-checked.` })
      onSaved()
    } catch (e) {
      toast({ tone: 'error', text: friendlyError((e as Error).message) })
    } finally {
      setSaving(false)
    }
  }

  return (
    <section>
      <h3 className="text-xl font-bold">Notes</h3>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <label className="flex-1">
          <span className="sr-only">Add a note for {name}</span>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => (e.metaKey || e.ctrlKey) && e.key === 'Enter' && save()}
            rows={2}
            placeholder={`Add a note for ${name}, e.g. “Temp 37.9, encouraged fluids.”`}
            className="w-full rounded-lg border border-line px-3 py-2"
          />
        </label>
        <button
          onClick={save}
          disabled={saving || text.trim().length < 3}
          className="self-start rounded-md bg-care px-4 py-2.5 font-bold text-white hover:bg-care-dark disabled:opacity-40"
        >
          {saving ? 'Saving…' : 'Save note'}
        </button>
      </div>
      <ol className="mt-4 divide-y divide-line">
        {notes.map((n) => (
          <li key={n.id} className="grid gap-x-4 py-2.5 sm:grid-cols-[11rem_1fr]">
            <span className="text-sm text-muted">
              {fmtDate(n.recorded_at)}
              <br className="hidden sm:block" /> {authorOf(n)}
            </span>
            <span>{n.note_text}</span>
          </li>
        ))}
      </ol>
      <Link to={`/psw?resident=${residentId}`} className="mt-2 inline-block text-sm font-bold text-care hover:underline">
        Open the quick note screen for {name}
      </Link>
    </section>
  )
}
