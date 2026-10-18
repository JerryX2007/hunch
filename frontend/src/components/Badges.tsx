import type { AlertStatus, Tier } from '../api/types'
import { STATUS_LABEL, TIER_LABEL, TIER_STYLE } from './format'

export function TierBadge({ tier, className = '' }: { tier: Tier; className?: string }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-sm font-bold ${TIER_STYLE[tier].pill} ${className}`}>
      {TIER_LABEL[tier]}
    </span>
  )
}

export function StatusBadge({ status }: { status: AlertStatus }) {
  const cls =
    status === 'open'
      ? 'border-care text-care'
      : status === 'needs_assessment'
        ? 'border-ink text-ink'
        : 'border-line text-muted'
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-sm ${cls}`}>
      {status === 'open' && <span className="h-2 w-2 rounded-full bg-care" aria-hidden />}
      {STATUS_LABEL[status]}
    </span>
  )
}
