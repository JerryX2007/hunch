import { useCallback, useRef, useState, type ReactNode } from 'react'
import { ToastCtx, type ToastMsg } from './toastContext'

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMsg[]>([])
  const nextId = useRef(1)

  const push = useCallback((t: Omit<ToastMsg, 'id'>) => {
    const id = nextId.current++
    setToasts((all) => [...all.slice(-2), { ...t, id }])
    window.setTimeout(() => setToasts((all) => all.filter((x) => x.id !== id)), t.tone === 'error' ? 9000 : 5000)
  }, [])

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast-in pointer-events-auto flex max-w-lg items-center gap-4 rounded-lg px-4 py-3 text-base shadow-lg ${t.tone === 'error' ? 'bg-urgent text-white' : 'bg-ink text-white'}`}
            role={t.tone === 'error' ? 'alert' : 'status'}
          >
            <span>{t.text}</span>
            {t.action && (
              <button
                className="shrink-0 font-bold underline underline-offset-2"
                onClick={() => {
                  t.action?.run()
                  setToasts((all) => all.filter((x) => x.id !== t.id))
                }}
              >
                {t.action.label}
              </button>
            )}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}
