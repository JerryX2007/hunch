import { Link } from 'react-router-dom'

// QR landing page for the demo: send people straight to the note screen.
export default function Join() {
  return (
    <div className="mx-auto max-w-md py-12 text-center">
      <h1 className="text-3xl font-bold">You’re a PSW on 2 West</h1>
      <p className="mt-3 text-lg text-muted">Notice something different about a resident? Log it in a few taps. The nurse sees it right away.</p>
      <Link to="/psw" className="mt-6 inline-block rounded-lg bg-care px-6 py-4 text-lg font-bold text-white hover:bg-care-dark">
        Log a note
      </Link>
    </div>
  )
}
