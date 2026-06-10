<template>
  <div class="flex items-center justify-center h-screen text-white">
    Authenticating...
  </div>
</template>

<script setup>
import { onMounted } from "vue"
import { useRouter } from "vue-router"
import api from "../services/api"

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

    // Store authentication and organisation details
    localStorage.setItem("access_token", res.data.access)
    localStorage.setItem("org_role", res.data.org_role || "")
    localStorage.setItem("org_slug", res.data.org_slug || "")

    // Store user identity for UI usage (greeting, profile, etc.)
    localStorage.setItem(
      "username",
      res.data.username || res.data.name || res.data.email || "User"
    )
    localStorage.setItem("email", res.data.email || "")

    console.log("GOOGLE RESPONSE:", res.data)
    // Redirect to org home 
    router.push("/org-home")

  } catch (error) {
    // If anything fails, log error and send user back to login
    console.error("Google authentication failed:", error)
    router.push("/login")
  }
})
</script>