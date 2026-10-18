import { Link } from 'react-router-dom'

// QR landing page: for now it just sends people to the note form.
export default function Join() {
  return (
    <div className="mx-auto max-w-md space-y-4 py-10 text-center">
      <h1 className="text-2xl font-bold">Welcome to 2 West</h1>
      <p className="text-slate-600">You're a PSW for this shift. Notice something different about a resident? Log it.</p>
      <Link to="/psw" className="inline-block rounded-lg bg-slate-900 px-5 py-3 font-semibold text-white">
        Start logging
      </Link>
    </div>
  )
}
