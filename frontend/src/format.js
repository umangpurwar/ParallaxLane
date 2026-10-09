// Display helpers shared by the views.
export function formatDate(value) {
  if (!value) return '–'
  return new Date(value).toLocaleString(undefined, { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export function humanize(text) {
  return text ? String(text).replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()) : ''
}

// The value an <input type="datetime-local"> needs, in the browser's time zone.
export function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function fromLocalInput(value) {
  return value ? new Date(value).toISOString() : null
}
