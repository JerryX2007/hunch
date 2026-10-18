import type { Alert, AlertStatus, CareNote, Health, ResidentOverview, ResidentSummary, RunResult, RunSummary } from './types'

// All requests go to /api/*. In dev, Vite proxies them to FastAPI on :8000.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* not JSON */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/health'),
  residents: (q?: string) => request<ResidentSummary[]>(`/residents${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  resident: (id: string) => request<ResidentOverview>(`/residents/${encodeURIComponent(id)}`),
  addNote: (id: string, note_text: string, author_role: string) =>
    request<{ note: CareNote; result: RunResult | null }>(`/residents/${encodeURIComponent(id)}/notes`, {
      method: 'POST',
      body: JSON.stringify({ note_text, author_role }),
    }),
  runCheck: () => request<RunSummary>('/history/run', { method: 'POST' }),
  setAlertStatus: (alertId: string, status: AlertStatus) =>
    request<Alert>(`/alerts/${alertId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
}
