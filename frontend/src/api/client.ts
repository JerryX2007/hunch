import type { Resident } from './types'

// All requests go to /api/*. In dev, Vite proxies them to FastAPI on :8000.
async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  health: () => get<{ status: string }>('/health'),
  residents: () => get<Resident[]>('/residents'),
  resident: (id: string) => get<Resident>(`/residents/${id}`),
}
