import { useParams } from 'react-router-dom'

export default function ResidentProfile() {
  const { residentId } = useParams()
  return <h1 className="text-xl font-semibold">Resident {residentId} — profile and recent activity</h1>
}
