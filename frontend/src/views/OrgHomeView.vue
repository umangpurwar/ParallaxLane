<template>
  <div class="flex items-center justify-center h-screen bg-brutal-dark font-sans p-6 overflow-hidden relative">
    
    <div class="absolute inset-0 pointer-events-none z-0">
      <div class="grid-line-v left-[33%]"></div>
      <div class="grid-line-v left-[66%]"></div>
    </div>

    <div class="relative z-10 max-w-md w-full bg-brutal-paper text-brutal-ink border-4 border-brutal-ink p-10 flex flex-col shadow-[12px_12px_0px_0px_rgba(239,63,35,1)]">
      
      <!-- LOGOUT -->
      <button
        @click="logout"
        class="absolute top-3 right-3 text-[9px] uppercase tracking-widest font-bold text-gray-500 hover:text-brutal-red"
      >
        Logout
      </button>

      <!-- GREETING -->
      <h1 class="text-3xl font-black tracking-tighter text-brutal-ink mb-2 uppercase italic text-center">
        Hello {{ username }}
      </h1>

      <p class="text-[10px] uppercase tracking-widest font-bold text-gray-500 mb-8 border-b-2 border-brutal-ink pb-4 text-center">
        Select your organisation
      </p>

      <!-- ORG LIST -->
      <div v-if="isLoading" class="text-center text-xs">
        Loading...
      </div>

      <div v-else-if="organisations.length" class="flex flex-col gap-4 mb-6">
        <button
          v-for="org in organisations"
          :key="org.slug"
          @click="selectOrg(org)"
          class="w-full py-4 text-[10px] uppercase tracking-super-wide font-bold border-2 border-brutal-ink text-brutal-ink hover:bg-brutal-ink hover:text-white transition-all"
        >
          {{ org.name }} ({{ org.role }})
        </button>
      </div>

      <div v-else class="text-center text-xs text-gray-500 mb-6">
        No organisations found
      </div>

      <!-- CREATE -->
      <button
        @click="router.push('/create-org')"
        class="w-full py-4 text-[10px] uppercase tracking-super-wide font-bold border-2 border-brutal-ink text-brutal-ink hover:bg-brutal-ink hover:text-white transition-all mb-4"
      >
        Create Organisation
      </button>

      <!-- JOIN -->
      <button
        @click="router.push('/join-org')"
        class="w-full py-4 text-[10px] uppercase tracking-super-wide font-bold border-2 border-brutal-ink text-brutal-ink hover:bg-brutal-ink hover:text-white transition-all"
      >
        Join Organisation
      </button>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { setAuthData } from '@/services/api'

const router = useRouter()

const username = ref('User')
const organisations = ref([])
const isLoading = ref(false)

onMounted(async () => {
  username.value =
    localStorage.getItem("username") ||
    localStorage.getItem("email") ||
    "User"

  await fetchOrganisations()
})

const fetchOrganisations = async () => {
  isLoading.value = true
  try {
    const res = await api.get("organisations/my/")
    organisations.value = res.data || []
  } catch (err) {
    console.error("Failed to fetch orgs", err)
  } finally {
    isLoading.value = false
  }
}

const logout = () => {
  localStorage.clear()
  router.push('/login')
}

const selectOrg = (org) => {
  // store selected org
  setAuthData({
    org_slug: org.slug,
    org_role: org.role,
    org_name: org.name
  })

  if (org.role === "owner" || org.role === "admin") {
    router.push('/admin')
  } else {
    router.push('/dashboard')
  }
}
</script>

