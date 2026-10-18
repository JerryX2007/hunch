import { useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { NewVitals, VitalField, VitalsTable } from '../api/types'
import { authorOf, fmtDate, friendlyError } from './format'
import { useToast } from './toastContext'

const COLS: { field: VitalField; label: string; unit: string }[] = [
  { field: 'temp_c', label: 'Temp', unit: '°C' },
  { field: 'spo2', label: 'SpO2', unit: '%' },
  { field: 'pulse', label: 'Pulse', unit: '' },
  { field: 'resp_rate', label: 'Breathing', unit: '' },
]

// Input limits match the API (backend/app/schemas.py NewVitals).
const INPUTS: { field: VitalField; label: string; hint: string; min: number; max: number; step: number }[] = [
  { field: 'temp_c', label: 'Temp °C', hint: 'e.g. 36.8', min: 30, max: 43, step: 0.1 },
  { field: 'spo2', label: 'SpO2 %', hint: 'e.g. 96', min: 50, max: 100, step: 1 },
  { field: 'pulse', label: 'Pulse', hint: 'e.g. 74', min: 25, max: 220, step: 1 },
  { field: 'resp_rate', label: 'Breathing /min', hint: 'e.g. 18', min: 4, max: 60, step: 1 },
  { field: 'bp_systolic', label: 'BP systolic', hint: 'e.g. 128', min: 50, max: 260, step: 1 },
  { field: 'bp_diastolic', label: 'BP diastolic', hint: 'e.g. 76', min: 20, max: 160, step: 1 },
]

function usualLine(u: VitalsTable['usual']) {
  const parts = [
    u.temperature != null && `${u.temperature.toFixed(1)} °C`,
    u.oxygen != null && `SpO2 ${Math.round(u.oxygen)}%`,
    u.pulse != null && `pulse ${Math.round(u.pulse)}`,
    u.breathing_rate != null && `breathing ${Math.round(u.breathing_rate)}/min`,
    u.blood_pressure != null && `systolic BP ${Math.round(u.blood_pressure)}`,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : null
}

/** Usual vitals, the last few readings (out-of-line values marked), and a form to chart a new set. */
export default function Vitals({
  residentId,
  name,
  vitals,
  onSaved,
}: {
  residentId: string
  name: string
  vitals: VitalsTable
  onSaved: () => void
}) {
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [values, setValues] = useState<Partial<Record<VitalField, string>>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const usual = usualLine(vitals.usual)
  const first = name.split(' ')[0]

  async function save(e: FormEvent) {
    e.preventDefault()
    const body: NewVitals = {}
    for (const i of INPUTS) {
      const raw = values[i.field]?.trim()
      if (raw) body[i.field] = Number(raw)
    }
    if (!Object.keys(body).length) {
      setError('Enter at least one measurement.')
      return
    }
    if ((body.bp_systolic == null) !== (body.bp_diastolic == null)) {
      setError('Enter both blood pressure numbers (e.g. 128 / 76).')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await api.addVitals(residentId, body)
      setValues({})
      setOpen(false)
      toast({ tone: 'ok', text: `Vitals saved for ${name} under your name. Re-checked.` })
      onSaved()
    } catch (err) {
      setError(friendlyError((err as Error).message))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xl font-bold">Vitals</h3>
        {!open && (
          <button onClick={() => setOpen(true)} className="rounded-md border border-care px-3 py-1.5 font-bold text-care hover:bg-care-soft">
            Add vitals
          </button>
        )}
      </div>
      <p className="mt-1 text-muted">
        {usual ? (
          <>
            Usual for {first}: <span className="text-ink">{usual}</span>
          </>
        ) : (
          'Not enough readings yet to know what’s usual; standard limits are used until there are three.'
        )}
      </p>

      {open && (
        <form onSubmit={save} className="mt-3 rounded-lg border border-line bg-ward p-4" aria-label={`Add vitals for ${name}`}>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {INPUTS.map((i) => (
              <label key={i.field} className="min-w-0">
                <span className="text-sm font-bold">{i.label}</span>
                <input
                  type="number"
                  inputMode={i.step < 1 ? 'decimal' : 'numeric'}
                  min={i.min}
                  max={i.max}
                  step={i.step}
                  value={values[i.field] ?? ''}
                  onChange={(e) => setValues((v) => ({ ...v, [i.field]: e.target.value }))}
                  placeholder={i.hint}
                  className="mt-1 w-full rounded-md border border-line bg-paper px-2.5 py-2"
                />
              </label>
            ))}
          </div>
          {error && (
            <p className="mt-3 text-urgent" role="alert">
              {error}
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="submit" disabled={saving} className="rounded-md bg-care px-4 py-2 font-bold text-white hover:bg-care-dark disabled:opacity-40">
              {saving ? 'Saving…' : 'Save vitals'}
            </button>
            <button
              type="button"
              onClick={() => {
                setOpen(false)
                setError(null)
              }}
              className="rounded-md border border-line bg-paper px-4 py-2 font-bold hover:border-care"
            >
              Cancel
            </button>
          </div>
          <p className="mt-2 text-sm text-muted">Any measurement can be left blank.</p>
        </form>
      )}

      {vitals.readings.length > 0 && (
        /* phones: one line per reading */
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line sm:hidden">
          {vitals.readings.map((r) => (
            <li key={r.id} className="px-3 py-2">
              <span className="block text-sm text-muted">
                {fmtDate(r.recorded_at)} · {authorOf(r)}
              </span>
              <span className="flex flex-wrap gap-x-3">
                {[
                  ['temp_c', r.temp_c != null && `${Number(r.temp_c).toFixed(1)} °C`],
                  ['spo2', r.spo2 != null && `SpO2 ${r.spo2}%`],
                  ['pulse', r.pulse != null && `P ${r.pulse}`],
                  ['resp_rate', r.resp_rate != null && `R ${r.resp_rate}`],
                  ['bp_systolic', r.bp_systolic != null && `BP ${r.bp_systolic}/${r.bp_diastolic}`],
                ]
                  .filter(([, text]) => text)
                  .map(([field, text]) => {
                    const why = r.flags[field as VitalField]
                    return (
                      <span key={field as string} className={why ? 'font-bold text-change' : ''}>
                        {text}
                        {why && <span className="sr-only"> (out of line: {why})</span>}
                      </span>
                    )
                  })}
              </span>
            </li>
          ))}
        </ul>
      )}
      {vitals.readings.length > 0 ? (
        <div className="mt-3 hidden overflow-x-auto rounded-lg border border-line sm:block">
          <table className="w-full min-w-[34rem] text-left">
            <thead className="bg-ward text-sm text-muted">
              <tr>
                <th className="px-3 py-2 font-bold">When</th>
                {COLS.map((c) => (
                  <th key={c.field} className="px-3 py-2 font-bold">
                    {c.label}
                  </th>
                ))}
                <th className="px-3 py-2 font-bold">BP</th>
                <th className="px-3 py-2 font-bold">By</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {vitals.readings.map((r) => {
                const bpFlag = r.flags.bp_systolic
                return (
                  <tr key={r.id}>
                    <td className="whitespace-nowrap px-3 py-2 text-sm text-muted">{fmtDate(r.recorded_at)}</td>
                    {COLS.map((c) => {
                      const v = r[c.field]
                      const why = r.flags[c.field]
                      return (
                        <td key={c.field} className={`whitespace-nowrap px-3 py-2 ${why ? 'font-bold text-change' : ''}`} title={why}>
                          {v == null ? <span className="text-muted">—</span> : `${c.field === 'temp_c' ? Number(v).toFixed(1) : v}${c.unit}`}
                          {why && <span className="sr-only"> (out of line: {why})</span>}
                        </td>
                      )
                    })}
                    <td className={`whitespace-nowrap px-3 py-2 ${bpFlag ? 'font-bold text-change' : ''}`} title={bpFlag}>
                      {r.bp_systolic == null ? <span className="text-muted">—</span> : `${r.bp_systolic}/${r.bp_diastolic}`}
                      {bpFlag && <span className="sr-only"> (out of line: {bpFlag})</span>}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-sm text-muted">{authorOf(r)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-3 text-muted">No vitals charted yet.</p>
      )}
      {vitals.readings.some((r) => Object.keys(r.flags).length > 0) && (
        <p className="mt-2 text-sm text-muted">
          <span className="font-bold text-change">Bold</span> values are out of line for {first}; “What changed” above says why. Limits
          from IDSA, McGeer and Loeb, measured against {first}’s own usual.
        </p>
      )}
    </section>
  )
}
