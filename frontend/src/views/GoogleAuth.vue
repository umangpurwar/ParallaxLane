<template>
  <div class="flex items-center justify-center h-screen text-white">
    Authenticating...
  </div>
</template>

<script setup>
import { onMounted } from "vue"
import { useRouter } from "vue-router"
import api, { setSessionData, redirectAfterAuth } from "../services/api"

const router = useRouter()

onMounted(async () => {
  // Extract hash parameters from URL after Google redirect
  const hash = window.location.hash
  const params = new URLSearchParams(hash.replace("#", ""))

  // Get ID token returned by Google
  const token = params.get("id_token")

  // If no token is present, redirect back to login
  if (!token) {
    router.push("/login")
    return
  }

  try {
    // Send token to backend for verification and login
    const res = await api.post("accounts/google/", { token })

    setSessionData({
      ...res.data,
      display_name: res.data.display_name || res.data.username || res.data.name,
    })
    redirectAfterAuth(router)

  } catch (error) {
    console.error("Google authentication failed:", error)
    const msg = error.response?.data?.error
    if (msg) {
      sessionStorage.setItem("auth_error", msg)
    }
    router.push("/login")
  }
})
</script>