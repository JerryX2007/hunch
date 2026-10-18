import type { AlertStatus, Tier } from '../api/types'
import { TIER_LABEL } from './format'

const TIER: Record<Tier, { label: string; cls: string }> = {
  urgent: { label: TIER_LABEL.urgent, cls: 'bg-red-600 text-white' },
  alert: { label: TIER_LABEL.alert, cls: 'bg-amber-500 text-white' },
  watch: { label: TIER_LABEL.watch, cls: 'bg-yellow-100 text-yellow-900 ring-1 ring-yellow-300' },
  baseline_limited: { label: TIER_LABEL.baseline_limited, cls: 'bg-slate-200 text-slate-700' },
  quiet: { label: TIER_LABEL.quiet, cls: 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200' },
}

export function TierBadge({ tier }: { tier: Tier }) {
  const t = TIER[tier]
  return <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${t.cls}`}>{t.label}</span>
}

const STATUS: Record<AlertStatus, string> = {
  open: 'New',
  reviewed: 'Reviewed',
  needs_assessment: 'Needs assessment',
  dismissed: 'Not useful',
}

export function StatusBadge({ status }: { status: AlertStatus }) {
  const cls =
    status === 'open'
      ? 'bg-blue-600 text-white'
      : status === 'needs_assessment'
        ? 'bg-violet-100 text-violet-900 ring-1 ring-violet-300'
        : 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'
  return <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>{STATUS[status]}</span>
}
