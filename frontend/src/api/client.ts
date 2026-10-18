import type { Alert, AlertStatus, CareNote, Health, Me, NewVitals, Profile, Resident, ResidentOverview, ResidentSummary, RunResult, RunSummary } from './types'

/** Fired when a nurse-only call comes back 401 (session ended); the sign-in state re-checks. */
export const SIGNED_OUT_EVENT = 'hunch:signed-out'

// All requests go to /api/*. In dev, Vite proxies them to FastAPI on :8000 (same origin, so
// the HttpOnly session cookie is sent automatically).
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    credentials: 'same-origin',
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event(SIGNED_OUT_EVENT))
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
  // auth
  me: () => request<Me>('/auth/me'),
  signIn: (email: string, password: string) =>
    request<Me>('/auth/signin', { method: 'POST', body: JSON.stringify({ email, password }) }),
  signOut: () => request<{ signed_in: boolean }>('/auth/logout', { method: 'POST' }),
  saveProfile: (full_name: string) =>
    request<Profile>('/profile/me', { method: 'PUT', body: JSON.stringify({ full_name }) }),
  // residents (signed out: only id + display_name come back)
  residents: (q?: string) => request<ResidentSummary[]>(`/residents${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  resident: (id: string) => request<ResidentOverview>(`/residents/${encodeURIComponent(id)}`),
  addNote: (id: string, note_text: string, author_role: string) =>
    request<{ note: CareNote; result: RunResult | null }>(`/residents/${encodeURIComponent(id)}/notes`, {
      method: 'POST',
      body: JSON.stringify({ note_text, author_role }),
    }),
  nextResidentId: () => request<{ id: string }>('/residents/next-id'),
  addVitals: (id: string, body: NewVitals) =>
    request<{ result: RunResult | null }>(`/residents/${encodeURIComponent(id)}/vitals`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  addResident: (body: { display_name: string; id?: string; first_note?: string; conditions?: string[] }) =>
    request<Resident>('/residents', { method: 'POST', body: JSON.stringify(body) }),
  runCheck: () => request<RunSummary>('/history/run', { method: 'POST' }),
  setAlertStatus: (alertId: string, status: AlertStatus) =>
    request<Alert>(`/alerts/${alertId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
}
