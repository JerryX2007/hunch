import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

export default function Home() {
  const [status, setStatus] = useState('checking…')

  useEffect(() => {
    api.health().then((r) => setStatus(r.status)).catch(() => setStatus('backend not reachable'))
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Hunch</h1>
      <p className="text-sm text-slate-600">Backend: {status}</p>
      <nav className="flex gap-4 underline">
        <Link to="/join">Join (QR landing)</Link>
        <Link to="/psw">PSW</Link>
        <Link to="/nurse">Nurse dashboard</Link>
      </nav>
    </div>
  )
}
