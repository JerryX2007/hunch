import type { Tier } from '../api/types'

export const TIER_ORDER: Tier[] = ['urgent', 'alert', 'watch', 'baseline_limited', 'quiet']

export const TIER_LABEL: Record<Tier, string> = {
  urgent: 'Urgent',
  alert: 'Change from usual',
  watch: 'Watch',
  baseline_limited: 'Not enough history',
  quiet: 'No change',
}

export function fmtDate(iso: string | null | undefined, withTime = true) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    ...(withTime ? { hour: 'numeric', minute: '2-digit' } : {}),
  })
}
