import type { AlertStatus, Tier } from '../api/types'

export const TIER_ORDER: Tier[] = ['urgent', 'alert', 'watch', 'baseline_limited', 'quiet']

// Words a nurse would use, not the engine's names.
export const TIER_LABEL: Record<Tier, string> = {
  urgent: 'Act now',
  alert: 'Changed from usual',
  watch: 'Keep an eye on',
  baseline_limited: 'Too new to compare',
  quiet: 'As usual',
}

export const TIER_HINT: Record<Tier, string> = {
  urgent: 'A serious event was noted. Follow the escalation procedure.',
  alert: 'Two or more things are different from this resident’s own normal.',
  watch: 'One thing is different from this resident’s own normal.',
  baseline_limited: 'Fewer than 7 days of notes, so there is no usual pattern yet.',
  quiet: 'Nothing lasting is different from this resident’s own normal.',
}

export const STATUS_LABEL: Record<AlertStatus, string> = {
  open: 'Not reviewed',
  reviewed: 'Reviewed',
  needs_assessment: 'Assessing',
  dismissed: 'Not useful',
}

// Colour classes per tier (pill = label, bar = row edge / dot).
export const TIER_STYLE: Record<Tier, { pill: string; bar: string }> = {
  urgent: { pill: 'bg-urgent text-white', bar: 'bg-urgent' },
  alert: { pill: 'bg-change-soft text-change', bar: 'bg-change-bar' },
  watch: { pill: 'bg-watch-soft text-watch', bar: 'bg-watch' },
  baseline_limited: { pill: 'bg-new-soft text-new', bar: 'bg-new' },
  quiet: { pill: 'bg-calm-soft text-calm', bar: 'bg-calm' },
}


export const NEEDS_ATTENTION: Tier[] = ['urgent', 'alert', 'watch']

export function fmtDate(iso: string | null | undefined, withTime = true) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    weekday: withTime ? 'short' : undefined,
    month: 'short',
    day: 'numeric',
    ...(withTime ? { hour: 'numeric', minute: '2-digit' } : {}),
  })
}

export function fmtDay(isoDate: string) {
  const d = new Date(`${isoDate.slice(0, 10)}T12:00:00`)
  return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

/** Every date from start to end inclusive (YYYY-MM-DD). */
export function daysBetween(start: string, end: string): string[] {
  const out: string[] = []
  const d = new Date(`${start.slice(0, 10)}T12:00:00`)
  const last = new Date(`${end.slice(0, 10)}T12:00:00`)
  while (d <= last && out.length < 31) {
    out.push(d.toISOString().slice(0, 10))
    d.setDate(d.getDate() + 1)
  }
  return out
}

/** The engine's category name, as a nurse would say it. */
export function niceLabel(label: string) {
  return label === 'Event' ? 'Serious event' : label
}

/** "tl" -> "Tagalog", "pa" -> "Punjabi"; the code itself if the browser doesn't know it. */
export function languageName(code: string | null | undefined) {
  if (!code) return 'another language'
  try {
    return new Intl.DisplayNames(['en'], { type: 'language' }).of(code) ?? code
  } catch {
    return code
  }
}

export function capitalize(text: string) {
  return text ? text[0].toUpperCase() + text.slice(1) : text
}

/** Who wrote a note: the nurse's name when she was signed in, else the role (e.g. PSW). */
export function authorOf(n: { author_name?: string | null; author_role?: string | null }) {
  return n.author_name || n.author_role || 'Staff'
}

/** "Evelyn Brooks – 2W-014", or just the ID when the resident has no separate name. */
export function residentLabel(r: { id: string; display_name: string }) {
  return r.display_name && r.display_name !== r.id ? `${r.display_name} – ${r.id}` : r.id
}

export function plural(n: number, one: string, many = `${one}s`) {
  return `${n} ${n === 1 ? one : many}`
}

/** Turn API errors into something a nurse can act on. */
export function friendlyError(message: string) {
  if (/check constraint|alerts_status_check/i.test(message))
    return 'The database doesn’t accept this review status yet. Ask whoever manages Supabase to run db/apply_to_live.sql.'
  if (/Failed to fetch|NetworkError|ECONNREFUSED/i.test(message))
    return 'Can’t reach the Hunch server. Check that run.py is still running.'
  return message
}
