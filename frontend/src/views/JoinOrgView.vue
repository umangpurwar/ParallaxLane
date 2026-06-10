<template>
  <div class="flex items-center justify-center h-screen bg-[#0a0a0a] text-white">
    
    <div class="relative p-10 border-4 border-black bg-white text-black shadow-[8px_8px_0px_#ef3f23] text-center w-full max-w-sm">
      
      <!-- BACK BUTTON -->
      <button
        @click="goBack"
        class="absolute top-3 left-3 text-[10px] uppercase tracking-widest font-bold text-gray-600 hover:text-[#ef3f23]"
      >
        ← Back
      </button>

      <h1 class="text-xl font-bold mb-6 uppercase tracking-widest">
        Join Organisation
      </h1>

      <input
        v-model="inviteCode"
        type="text"
        placeholder="Enter Invite Code"
        class="border-2 border-black px-4 py-3 mb-4 w-full"
        :disabled="isLoading"
      />

      <p v-if="errorMessage" class="text-red-600 text-xs mb-3">
        {{ errorMessage }}
      </p>

      <button
        @click="joinOrg"
        :disabled="isLoading"
        class="w-full bg-black text-white py-3 uppercase tracking-widest font-bold hover:bg-[#ef3f23] disabled:opacity-50"
      >
        {{ isLoading ? "Joining..." : "Join" }}
      </button>

    </div>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { useRouter } from "vue-router"
import api, { setAuthData } from "@/services/api"

const router = useRouter()

const inviteCode = ref("")
const errorMessage = ref("")
const isLoading = ref(false)

const goBack = () => {
  router.push("/org-home")
}

const joinOrg = async () => {
  errorMessage.value = ""

  const code = inviteCode.value.trim()

  if (!code) {
    errorMessage.value = "Invite code required"
    return
  }

  isLoading.value = true

  try {
    const res = await api.post("organisations/join/", {
      code
    })

    const data = res.data

    setAuthData({
      org_slug: data.slug,
      org_role: data.role,
      org_name: data.name,
      org_plan: data.plan
    })

    // Direct redirect (correct flow)
    if (data.role === "owner" || data.role === "admin") {
      router.push("/admin")
    } else {
      router.push("/dashboard")
    }

  } catch (err) {
    if (err.response && err.response.data) {
      errorMessage.value =
        err.response.data.error || "Invalid or expired invite code"
    } else {
      errorMessage.value = "Network error. Please try again."
    }
  } finally {
    isLoading.value = false
  }
}
</script>

