/**
 * Google OAuth redirect URI must match exactly what is registered in
 * Google Cloud Console → APIs & Services → Credentials → OAuth client →
 * Authorized redirect URIs.
 */
export function getGoogleRedirectUri() {
  const configured = import.meta.env.VITE_GOOGLE_REDIRECT_URI?.trim()
  if (configured) {
    return configured
  }
  return `${window.location.origin}/auth/google`
}

export function isGoogleAuthConfigured() {
  return Boolean(import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim())
}

export function startGoogleLogin() {
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim()
  if (!clientId) {
    alert("Google sign-in is not configured. Set VITE_GOOGLE_CLIENT_ID in frontend/.env")
    return
  }

  const nonce = crypto.randomUUID()
  sessionStorage.setItem("google_oauth_nonce", nonce)

  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: getGoogleRedirectUri(),
    response_type: "id_token",
    scope: "openid email profile",
    nonce,
  })

  window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params}`
}
