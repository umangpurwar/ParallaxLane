// Who is signed in, as reported by the server (GET accounts/me/). The UI decides which
// panel to show from this, but every permission is enforced again by the backend.
import { reactive, readonly } from 'vue'
import { auth } from '@/api/endpoints'
import { tokens, setSessionExpiredHandler } from '@/api/client'

const state = reactive({ me: null, loaded: false, expired: false })

export const session = {
  state: readonly(state),

  isSignedIn: () => Boolean(tokens.get().access),

  async login(email, password) {
    const data = await auth.login(email.trim().toLowerCase(), password)
    tokens.set(data.access, data.refresh)
    state.expired = false
    return this.load(true)
  },

  async load(force = false) {
    if (state.loaded && !force) return state.me
    state.me = await auth.me()
    state.loaded = true
    return state.me
  },

  async logout() {
    const { refresh } = tokens.get()
    if (refresh) {
      try { await auth.logout(refresh) } catch { /* the token may already be invalid */ }
    }
    this.reset()
  },

  reset() {
    tokens.clear()
    state.me = null
    state.loaded = false
  },

  markExpired() {
    this.reset()
    state.expired = true
  },

  // Approved organisations the user administers.
  adminOrgs() {
    return (state.me?.memberships || []).filter((m) => m.is_admin && m.status === 'approved')
  },

  // Where to send the user after login, from server data only.
  homeRoute() {
    const me = state.me
    if (!me) return { name: 'login' }
    if (me.is_super_admin) return { name: 'platform-overview' }
    const orgs = this.adminOrgs()
    if (orgs.length === 1) return { name: 'org-overview', params: { slug: orgs[0].slug } }
    if (orgs.length > 1) return { name: 'org-picker' }
    if (me.applications.length) return { name: 'application' }
    if (me.memberships.length) return { name: 'members-only' }
    return { name: 'apply' }
  },
}

setSessionExpiredHandler(() => session.markExpired())
