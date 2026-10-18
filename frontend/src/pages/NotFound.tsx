import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="py-12">
      <h1 className="text-2xl font-bold">This page doesn’t exist.</h1>
      <Link to="/nurse" className="mt-3 inline-block font-bold text-care underline">
        Go to residents
      </Link>
    </div>
  )
}
