<template>
  <div class="flex items-center justify-center h-screen bg-brutal-dark font-sans p-6 overflow-hidden relative">
    
    <div class="absolute inset-0 pointer-events-none z-0">
      <div class="grid-line-v left-[33%]"></div>
      <div class="grid-line-v left-[66%]"></div>
    </div>

    <div class="relative z-10 max-w-md w-full bg-brutal-paper text-brutal-ink border-4 border-brutal-ink p-10 flex flex-col shadow-[12px_12px_0px_0px_rgba(239,63,35,1)]">
      
      <button
        @click="logout"
        class="absolute top-3 right-3 text-[9px] uppercase tracking-widest font-bold text-gray-500 hover:text-brutal-red"
      >
        Logout
      </button>

      <h1 class="text-3xl font-black tracking-tighter text-brutal-ink mb-2 uppercase italic text-center">
        Hello {{ username }}
      </h1>

      <p class="text-[10px] uppercase tracking-widest font-bold text-gray-500 mb-8 border-b-2 border-brutal-ink pb-4 text-center">
        Select your organisation to continue
      </p>

      <div v-if="isLoading" class="text-center text-xs">
        Loading organisations...
      </div>

      <div v-else-if="organisations.length" class="flex flex-col gap-4 mb-6">
        <button
          v-for="org in organisations"
          :key="org.slug"
          @click="selectOrg(org)"
          :disabled="isSelecting"
          class="w-full py-4 text-[10px] uppercase tracking-super-wide font-bold border-2 border-brutal-ink text-brutal-ink hover:bg-brutal-ink hover:text-white transition-all disabled:opacity-50"
        >
          {{ org.name }}
          <span class="block text-[8px] mt-1 opacity-70">{{ org.role }} · {{ (org.plan || 'free').toUpperCase() }}</span>
        </button>
      </div>

      <div v-else class="text-center text-xs text-gray-500 mb-6">
        No organisations found. Create one or join with an invite code.
      </div>

      <p v-if="errorMessage" class="text-[10px] uppercase font-bold text-brutal-red text-center mb-4">
        {{ errorMessage }}
      </p>

      <button
        @click="router.push('/create-org')"
        class="w-full py-4 text-[10px] uppercase tracking-super-wide font-bold border-2 border-brutal-ink text-brutal-ink hover:bg-brutal-ink hover:text-white transition-all mb-4"
      >
        Create Organisation
      </button>

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
import api, {
  clearOrgContext,
  setOrgContext,
  redirectAfterOrgSelect,
  logout as apiLogout,
} from '@/services/api'

const router = useRouter()

const username = ref('User')
const organisations = ref([])
const isLoading = ref(false)
const isSelecting = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  clearOrgContext()

  username.value =
    localStorage.getItem("username") ||
    localStorage.getItem("email") ||
    "User"

  await fetchOrganisations()
})

const fetchOrganisations = async () => {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const res = await api.get("organisations/my/")
    organisations.value = res.data?.organisations || []
  } catch (err) {
    console.error("Failed to fetch orgs", err)
    errorMessage.value = "Could not load organisations."
  } finally {
    isLoading.value = false
  }
}

const logout = async () => {
  await apiLogout()
  router.push('/login')
}

const selectOrg = async (org) => {
  isSelecting.value = true
  errorMessage.value = ''

  try {
    const res = await api.post(`organisations/${org.slug}/switch/`)
    setOrgContext(res.data)

    const role = res.data.role || res.data.org_role || org.role
    redirectAfterOrgSelect(router, role)
  } catch (err) {
    console.error("Failed to switch organisation", err)
    errorMessage.value = err.response?.data?.error || "Failed to select organisation."
  } finally {
    isSelecting.value = false
  }
}
</script>
