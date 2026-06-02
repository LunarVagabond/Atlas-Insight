import { reactive } from 'vue'

export type ToastVariant = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: number
  message: string
  variant: ToastVariant
  duration: number
}

let _nextId = 1

const _toasts = reactive<Toast[]>([])

function show(message: string, variant: ToastVariant = 'info', duration = 3500) {
  const id = _nextId++
  _toasts.push({ id, message, variant, duration })
  setTimeout(() => dismiss(id), duration)
}

function dismiss(id: number) {
  const idx = _toasts.findIndex(t => t.id === id)
  if (idx !== -1) _toasts.splice(idx, 1)
}

export function useToast() {
  return {
    toasts: _toasts,
    success: (msg: string, duration?: number) => show(msg, 'success', duration),
    error: (msg: string, duration?: number) => show(msg, 'error', duration ?? 5000),
    info: (msg: string, duration?: number) => show(msg, 'info', duration),
    warning: (msg: string, duration?: number) => show(msg, 'warning', duration),
    dismiss,
  }
}
