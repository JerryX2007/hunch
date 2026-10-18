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

/**
 * Some Chrome-based browsers (Brave, browsers inside desktop apps) have the speech API but
 * not Google's speech service behind it, so every attempt fails with a "network" error.
 */
function lacksSpeechService() {
  const n = navigator as Navigator & { brave?: unknown }
  return Boolean(n.brave) || /\bElectron\//.test(navigator.userAgent)
}

/**
 * Safari, and every browser on iPhone/iPad (they all use Safari's engine). Its "continuous"
 * mode switches the microphone off and on between phrases, and it sometimes ends without
 * marking the last words final, so there we listen for one phrase per tap.
 */
function isSafariEngine() {
  const ua = navigator.userAgent
  return /AppleWebKit/.test(ua) && !/(Chrome|Chromium|Edg)\//.test(ua)
}

const USE_OTHER =
  'Open Hunch in Google Chrome, Edge or Safari, or use your keyboard’s own dictation (the microphone key).'

const ERRORS: Record<string, string> = {
  'not-allowed': 'The microphone is blocked. Allow it in the browser’s address bar, then try again.',
  'service-not-allowed':
    'Voice input is turned off on this device. Turn on Dictation in the keyboard settings (System Settings › Keyboard on a Mac, Settings › General › Keyboard on iPhone), then try again.',
  'no-speech': 'Didn’t hear anything. Tap Speak and try again.',
  'audio-capture': 'No microphone found.',
  network: `This browser can’t reach a speech service. ${USE_OTHER}`,
}

/** "ate less than usual" -> "Ate less than usual." so the note reads (and is read) as a sentence. */
function asSentence(text: string) {
  const t = text.trim().replace(/\s+/g, ' ')
  if (!t) return ''
  const s = t[0].toUpperCase() + t.slice(1)
  return /[.!?]$/.test(s) ? s : `${s}.`
}

/**
 * A "Speak" button: tap to start, talk, tap to stop (Safari stops by itself after a pause).
 * Each finished phrase is passed to onText; words still being recognised show live
 * underneath. Uses the browser's own speech recognition (Chrome, Edge, Safari); in other
 * browsers it says so instead.
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
  useEffect(
    () => () => {
      const r = rec.current
      rec.current = null // tells onend not to hand over leftover words after we've gone
      r?.abort()
    },
    [],
  )

  const Ctor = recognizerCtor()
  if (!Ctor || !window.isSecureContext || lacksSpeechService()) {
    return (
      <p className="text-sm text-muted">
        {!Ctor || lacksSpeechService()
          ? `Voice input isn’t available in this browser. ${USE_OTHER}`
          : 'Voice input needs a secure (https) page.'}
      </p>
    )
  }

  function start() {
    if (!Ctor || rec.current) return
    if (!navigator.onLine) {
      setError('You’re offline. Voice input needs the internet; you can still type.')
      return
    }
    setError(null)
    const r = new Ctor()
    // The note reader understands English, so ask for English regardless of browser locale.
    r.lang = 'en-CA'
    r.continuous = !isSafariEngine()
    r.interimResults = true
    let used = 0 // results already handed to onText (some browsers repeat final results)
    let pending = '' // words heard but not yet marked final
    r.onresult = (e) => {
      let live = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i]
        if (res.isFinal) {
          if (i < used) continue
          used = i + 1
          const s = asSentence(res[0].transcript)
          if (s) sink.current(s)
        } else {
          live += res[0].transcript
        }
      }
      pending = live
      setInterim(live)
    }
    r.onerror = (e) => {
      if (e.error !== 'aborted') setError(ERRORS[e.error] ?? 'Voice input stopped. Try again.')
    }
    r.onend = () => {
      // Safari can stop without marking the last words final; keep them rather than lose them.
      const left = asSentence(pending)
      if (left && rec.current === r) sink.current(left)
      pending = ''
      if (rec.current === r) rec.current = null
      setListening(false)
      setInterim('')
    }
    rec.current = r
    try {
      r.start()
      setListening(true)
    } catch {
      rec.current = null
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
        title="Your browser turns speech into text (Chrome uses Google’s speech service, Safari uses Apple’s)."
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
