// Small notification queue shown by ToastHost.
import { reactive } from 'vue'

export const toasts = reactive([])
let nextId = 1

export function notify(message, kind = 'info', timeout = 4000) {
  const id = nextId++
  toasts.push({ id, message, kind })
  setTimeout(() => dismiss(id), timeout)
}

export function dismiss(id) {
  const index = toasts.findIndex((t) => t.id === id)
  if (index !== -1) toasts.splice(index, 1)
}

export const toast = {
  success: (message) => notify(message, 'success'),
  error: (error) => notify(typeof error === 'string' ? error : error?.message || 'Something went wrong.', 'error', 6000),
}
