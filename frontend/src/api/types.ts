// Keep in sync with backend/app/schemas.py and the dicts returned by backend/app/history/service.py

export type Tier = 'urgent' | 'alert' | 'watch' | 'baseline_limited' | 'quiet'
export type AlertStatus = 'open' | 'reviewed' | 'needs_assessment' | 'dismissed'

export interface Resident {
  id: string
  display_name: string
  baseline_start: string | null
  baseline_end: string | null
}

export interface AlertSummary {
  id: string
  resident_id: string
  title: string
  summary: string | null
  status: AlertStatus
  urgent: boolean
  created_at: string
}

export interface ResidentSummary extends Resident {
  tier: Tier
  title: string | null
  urgent: boolean
  reasons: string[]
  changes: string[]
  days: number | null
  alert: AlertSummary | null
  last_note_at: string | null
  last_note: { note_text: string; recorded_at: string; author_role: string | null; author_name?: string | null } | null
}

export interface Evidence {
  note_id: string | null
  recorded_at: string
  author_role: string | null
  author_name?: string | null
  note_text: string
  phrase: string
}

export interface Finding {
  key: string
  match_key: string
  persisting: boolean
  recent_days: string[]
  baseline_rate: number
  recent_rate: number
  reason: string
  urgent: boolean
  evidence?: Evidence[]
}

export interface HistoryCheck {
  resident_id: string
  as_of: string
  tier: Tier
  alert: boolean
  urgent: boolean
  baseline_limited: boolean
  baseline_days: number
  window: { baseline_start: string | null; baseline_end: string | null; recent_start?: string; recent_end?: string }
  findings: Finding[]
  reasons: string[]
  ruled_out: string[]
  title: string
  categories: string[]
  duration_days: number
}

export interface Narrative {
  summary: string
  claims: { text: string; evidence_ids: string[] }[]
  uncertainties: string[]
  source: 'llm' | 'template' | 'none'
}

export interface Alert extends AlertSummary {
  explanation: (HistoryCheck & { fingerprint?: string; narrative?: Narrative }) | null
}

export interface CaseMatch {
  historical_case_id: string
  rank: number
  case_summary: string
  documented_outcome: string
  outcome_category: string | null
  disposition: string | null
  limitations: string
  duration_days: number
  total_score: number
  structured_score: number
  temporal_score: number
  shared_signals: string[]
  case_only_signals: string[]
  resident_only_signals: string[]
  differences: { kind: string; text: string }[]
}

export interface SimilarCases {
  alert_id: string
  note: string
  outcomes: { outcome_category: string | null; n: number }[]
  cases: CaseMatch[]
}

export interface CareNote {
  id: string
  resident_id: string
  note_text: string
  recorded_at: string
  author_role: string | null
  author_name?: string | null
}

export interface ResidentOverview {
  resident: Resident
  check: HistoryCheck | null
  alert: Alert | null
  similar: SimilarCases | null
  notes: CareNote[]
}

export interface Health {
  status: string
  mode?: 'demo' | 'supabase'
  database?: string
  llm: boolean
}

export interface RunResult {
  resident_id: string
  tier: Tier
  title: string | null
  reasons: string[]
  alert_id?: string
  suppressed?: boolean
}

export interface RunSummary {
  mode: string
  as_of: string | null
  residents: RunResult[]
  alerts: number
}

export type StaffRole = 'nurse'

export interface Profile {
  id: string
  full_name: string
  role: StaffRole
}

export interface Me {
  signed_in: boolean
  user: { id: string; email: string | null } | null
  profile: Profile | null
  is_nurse: boolean
  demo_login: { email: string; password: string } | null
}
