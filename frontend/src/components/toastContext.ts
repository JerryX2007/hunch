import { createContext, useContext } from 'react'

export interface ToastMsg {
  id: number
  text: string
  tone: 'ok' | 'error'
  action?: { label: string; run: () => void }
}

export const ToastCtx = createContext<(t: Omit<ToastMsg, 'id'>) => void>(() => {})

/** Show a short message at the bottom of the screen, optionally with an action like Undo. */
export function useToast() {
  return useContext(ToastCtx)
}
