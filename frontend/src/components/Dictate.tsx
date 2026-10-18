import { useEffect, useRef, useState } from 'react'

// Minimal types for the Web Speech API (not in TypeScript's DOM lib everywhere).
interface SpeechAlternative {
  transcript: string
}
interface SpeechResult {
  isFinal: boolean
  0: SpeechAlternative
}
interface SpeechEvent {
  resultIndex: number
  results: ArrayLike<SpeechResult>
}
interface Recognizer {
  lang: string
  continuous: boolean
  interimResults: boolean
  onresult: ((e: SpeechEvent) => void) | null
  onerror: ((e: { error: string }) => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
  abort: () => void
}
type RecognizerCtor = new () => Recognizer

function recognizerCtor(): RecognizerCtor | null {
  const w = window as unknown as { SpeechRecognition?: RecognizerCtor; webkitSpeechRecognition?: RecognizerCtor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

const ERRORS: Record<string, string> = {
  'not-allowed': 'The microphone is blocked. Allow it in the browser’s address bar, then try again.',
  'service-not-allowed': 'The microphone is blocked. Allow it in the browser’s address bar, then try again.',
  'no-speech': 'Didn’t hear anything. Tap Speak and try again.',
  'audio-capture': 'No microphone found.',
  network: 'Speech-to-text needs an internet connection.',
}

/** "ate less than usual" -> "Ate less than usual." so the note reads (and is read) as a sentence. */
function asSentence(text: string) {
  const t = text.trim().replace(/\s+/g, ' ')
  if (!t) return ''
  const s = t[0].toUpperCase() + t.slice(1)
  return /[.!?]$/.test(s) ? s : `${s}.`
}

/**
 * A "Speak" button: tap to start, talk, tap to stop. Each finished phrase is passed to
 * onText; words still being recognised show live underneath. Uses the browser's own speech
 * recognition (Chrome, Edge, Safari); in other browsers it says so instead.
 */
export default function Dictate({ onText, large = false }: { onText: (sentence: string) => void; large?: boolean }) {
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [error, setError] = useState<string | null>(null)
  const rec = useRef<Recognizer | null>(null)
  const sink = useRef(onText)
  useEffect(() => {
    sink.current = onText
  }, [onText])
  useEffect(() => () => rec.current?.abort(), [])

  const Ctor = recognizerCtor()
  if (!Ctor || !window.isSecureContext) {
    return (
      <p className="text-sm text-muted">
        {Ctor
          ? 'Voice input needs a secure (https) page.'
          : 'Voice input works in Chrome, Edge and Safari.'}
      </p>
    )
  }

  function start() {
    if (!Ctor) return
    setError(null)
    const r = new Ctor()
    // The note reader understands English, so ask for English regardless of browser locale.
    r.lang = 'en-CA'
    r.continuous = true
    r.interimResults = true
    r.onresult = (e) => {
      let live = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i]
        if (res.isFinal) {
          const s = asSentence(res[0].transcript)
          if (s) sink.current(s)
        } else {
          live += res[0].transcript
        }
      }
      setInterim(live)
    }
    r.onerror = (e) => {
      if (e.error !== 'aborted') setError(ERRORS[e.error] ?? 'Voice input stopped. Try again.')
    }
    r.onend = () => {
      setListening(false)
      setInterim('')
      rec.current = null
    }
    rec.current = r
    try {
      r.start()
      setListening(true)
    } catch {
      setError('Voice input couldn’t start. Try again.')
    }
  }

  function stop() {
    rec.current?.stop()
  }

  const size = large ? 'px-5 py-3 text-lg' : 'px-4 py-2'
  return (
    <div className="min-w-0">
      <button
        type="button"
        onClick={listening ? stop : start}
        aria-pressed={listening}
        title="Your browser turns speech into text (in Chrome, using Google’s speech service)."
        className={`inline-flex items-center gap-2 rounded-lg border-2 font-bold transition-colors ${size} ${
          listening ? 'border-urgent bg-urgent text-white' : 'border-care bg-paper text-care hover:bg-care-soft'
        }`}
      >
        {listening ? (
          <span className="relative flex h-3 w-3" aria-hidden>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-white" />
          </span>
        ) : (
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
            <rect x="9" y="3" width="6" height="11" rx="3" />
            <path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" />
          </svg>
        )}
        {listening ? 'Listening… tap to stop' : 'Speak'}
      </button>
      {listening && (
        <p className="mt-2 min-h-6 text-muted" aria-live="polite">
          {interim ? `“${interim}”` : 'Go ahead, I’m listening.'}
        </p>
      )}
      {error && (
        <p className="mt-2 text-sm text-urgent" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
