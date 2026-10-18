import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import Dictate from './Dictate'
import { friendlyError } from './format'
import { useToast } from './toastContext'

/** New admission: name, unit ID (next free one filled in), optional first note. */
export default function AddPatient({ onAdded }: { onAdded: () => void }) {
  const navigate = useNavigate()
  const toast = useToast()
  const [name, setName] = useState('')
  const [id, setId] = useState('')
  const [suggested, setSuggested] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    api
      .nextResidentId()
      .then((r) => {
        if (!live) return
        setSuggested(r.id)
        setId((cur) => cur || r.id)
      })
      .catch(() => {})
    return () => {
      live = false
    }
  }, [])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    setError(null)
    try {
      const created = await api.addResident({
        display_name: name.trim(),
        id: id.trim() || undefined,
        first_note: note.trim() || undefined,
      })
      onAdded()
      toast({ tone: 'ok', text: `Added ${created.display_name} (${created.id}).` })
      navigate(`/nurse/residents/${created.id}`)
    } catch (err) {
      setError(friendlyError((err as Error).message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-line bg-paper px-5 py-6 sm:px-6" aria-labelledby="add-title">
      <h2 id="add-title" className="text-2xl font-bold">
        Add a patient
      </h2>
      <p className="mt-1 max-w-prose text-muted">
        For a new admission. Hunch needs about a week of notes to learn their usual pattern; until then they show as “too new to
        compare”.
      </p>

      <label className="mt-6 block max-w-md">
        <span className="font-bold">Full name</span>
        <input
          autoFocus
          required
          maxLength={120}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Eleanor Park"
          className="mt-1 w-full rounded-lg border border-line px-3.5 py-3 text-base"
        />
      </label>

      <label className="mt-4 block max-w-xs">
        <span className="font-bold">Unit ID</span>
        <input
          value={id}
          maxLength={40}
          onChange={(e) => setId(e.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, ''))}
          className="mt-1 w-full rounded-lg border border-line px-3.5 py-3 text-base"
        />
        <span className="mt-1 block text-sm text-muted">
          {suggested && id === suggested ? 'The next free ID. Change it if your unit uses another.' : 'Letters, numbers and dashes.'}
        </span>
      </label>

      <label className="mt-4 block max-w-xl">
        <span className="font-bold">Admission note</span> <span className="text-sm text-muted">(optional)</span>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          maxLength={2000}
          placeholder="e.g. Admitted from hospital. Walks with a cane, eats independently."
          className="mt-1 w-full rounded-lg border border-line px-3 py-2"
        />
        <span className="mt-1 block text-sm text-muted">Saved as their first note, under your name.</span>
      </label>
      <div className="mt-2">
        <Dictate onText={(s) => setNote((t) => (t.trim() ? `${t.trim()} ${s}` : s))} />
      </div>

      {error && (
        <p className="mt-4 max-w-xl rounded-md bg-urgent-soft p-3 text-urgent" role="alert">
          {error}
        </p>
      )}

      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={busy || !name.trim()}
          className="rounded-lg bg-care px-5 py-3 font-bold text-white hover:bg-care-dark disabled:opacity-40"
        >
          {busy ? 'Adding…' : 'Add patient'}
        </button>
        <button
          type="button"
          onClick={() => navigate('/nurse')}
          className="rounded-lg border border-line bg-paper px-5 py-3 font-bold hover:border-care"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
