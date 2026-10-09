// One axios instance for the whole dashboard: base URL from env, bearer token,
// a single in-flight token refresh, and errors normalised to { code, message, status, fields }.
import axios from 'axios'

const TOKENS_KEY = 'pl_admin_tokens'
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/'

// Tokens live in sessionStorage: they survive a reload but not closing the tab.
export const tokens = {
  get() {
    try { return JSON.parse(sessionStorage.getItem(TOKENS_KEY)) || {} } catch { return {} }
  },
  set(access, refresh) { sessionStorage.setItem(TOKENS_KEY, JSON.stringify({ access, refresh })) },
  clear() { sessionStorage.removeItem(TOKENS_KEY) },
}

let onSessionExpired = () => {}
export function setSessionExpiredHandler(fn) { onSessionExpired = fn }

export const http = axios.create({ baseURL, timeout: 20000, headers: { 'Content-Type': 'application/json' } })
export const plain = axios.create({ baseURL, timeout: 20000 })

http.interceptors.request.use((config) => {
  const { access } = tokens.get()
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

let refreshing = null
function refreshTokens() {
  // Every 401 that arrives while one refresh is running waits for that same refresh,
  // because the server rotates refresh tokens and a second refresh would fail.
  if (!refreshing) {
    const { refresh } = tokens.get()
    refreshing = (refresh ? plain.post('token/refresh/', { refresh }) : Promise.reject(new Error('no refresh token')))
      .then(({ data }) => { tokens.set(data.access, data.refresh); return data.access })
      .finally(() => { refreshing = null })
  }
  return refreshing
}

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && original && !original._retried && tokens.get().refresh) {
      original._retried = true
      try {
        const access = await refreshTokens()
        original.headers.Authorization = `Bearer ${access}`
        return http(original)
      } catch {
        tokens.clear()
        onSessionExpired()
      }
    } else if (error.response?.status === 401) {
      tokens.clear()
      onSessionExpired()
    }
    return Promise.reject(normaliseError(error))
  },
)

export function normaliseError(error) {
  if (error?.isApiError) return error
  const response = error?.response
  const out = { isApiError: true, status: response?.status || 0, code: 'unknown', message: 'Something went wrong. Try again.', fields: {} }
  if (!response) {
    out.code = 'network'
    out.message = 'Cannot reach the server. Check your connection or try again shortly.'
    return out
  }
  const data = response.data
  out.raw = data
  if (response.status === 429) {
    out.code = 'rate_limited'
    out.message = 'Too many requests. Wait a minute and try again.'
  }
  if (data && typeof data === 'object' && !(data instanceof Blob)) {
    if (data.code) out.code = data.code
    const msg = data.error || data.detail
    if (typeof msg === 'string') out.message = msg
    for (const [key, value] of Object.entries(data)) {
      if (Array.isArray(value) && typeof value[0] === 'string') {
        out.fields[key] = value[0]
        if (key === 'non_field_errors' || !msg) out.message = key === 'non_field_errors' ? value[0] : `${key.replace(/_/g, ' ')}: ${value[0]}`
      }
    }
  } else if (response.status >= 500) {
    out.message = 'The server had a problem. Try again in a moment.'
  }
  if (response.status === 403 && out.code === 'unknown') out.code = 'forbidden'
  return out
}

// Login and registration go through the plain client (no token, no refresh).
export async function publicPost(url, body) {
  try {
    return (await plain.post(url, body)).data
  } catch (error) {
    throw normaliseError(error)
  }
}
