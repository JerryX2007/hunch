import { Navigate } from 'react-router-dom'

// The nurse dashboard is the main screen.
export default function Home() {
  return <Navigate to="/nurse" replace />
}
