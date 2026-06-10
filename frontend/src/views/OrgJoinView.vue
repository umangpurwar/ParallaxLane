<template>
  <div class="flex items-center justify-center h-screen bg-brutal-dark font-sans p-6 overflow-hidden relative">
    
    <div class="absolute inset-0 pointer-events-none z-0">
      <div class="grid-line-v left-[33%]"></div>
      <div class="grid-line-v left-[66%]"></div>
    </div>

    <div class="relative z-10 max-w-md w-full bg-brutal-paper text-brutal-ink border-4 border-brutal-ink p-10 flex flex-col shadow-[12px_12px_0px_0px_rgba(239,63,35,1)]">
      
      <h1 class="text-4xl font-black tracking-tighter text-brutal-ink mb-2 uppercase italic">
        Join Organisation
      </h1>
      <p class="text-[10px] uppercase tracking-widest font-bold text-gray-500 mb-8 border-b-2 border-brutal-ink pb-4">
        Enter your secure invite code below
      </p>

      <form @submit.prevent="joinOrg" class="flex flex-col gap-6">
        <div class="relative">
          <input
            v-model="inviteCode"
            type="text"
            placeholder="INVITE CODE"
            class="w-full bg-white border-2 border-brutal-border py-4 px-4 text-center text-brutal-ink font-bold tracking-[0.3em] uppercase placeholder-gray-400 focus:outline-none focus:border-brutal-ink transition-colors"
            :disabled="isSubmitting"
          />
        </div>

        <p v-if="errorMessage" class="text-[10px] uppercase tracking-widest font-bold text-brutal-red text-center leading-tight">
          {{ errorMessage }}
        </p>

        <button
          type="submit"
          :disabled="isSubmitting || !inviteCode.trim()"
          class="w-full py-5 text-[11px] uppercase tracking-[0.4em] font-black transition-all transform active:scale-95 border-b-4 border-r-4 border-gray-600"
          :class="(isSubmitting || !inviteCode.trim()) ? 'bg-gray-300 text-gray-500 cursor-not-allowed border-transparent' : 'bg-brutal-ink text-white hover:bg-brutal-red hover:border-brutal-ink cursor-pointer'"
        >
          {{ isSubmitting ? 'Joining...' : 'Join Organisation' }}
        </button>
      </form>

      <div class="mt-8 text-center">
        <router-link to="/create-org" class="text-[9px] uppercase tracking-widest font-bold text-gray-500 hover:text-brutal-red transition-colors">
          Have no invite? Create your own organisation
        </router-link>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { setAuthData } from '@/services/api'

const router = useRouter()

const inviteCode = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

onMounted(() => {
  const orgSlug = localStorage.getItem("org_slug")
  if (orgSlug) {
    router.push('/dashboard')
  }
})

const joinOrg = async () => {
  errorMessage.value = ''

  if (!inviteCode.value.trim()) {
    errorMessage.value = 'Please enter an invite code.'
    return
  }

  isSubmitting.value = true

  try {
    const response = await api.post('organisations/join/', {
      code: inviteCode.value.trim()
    })

    const data = response.data

    // ✅ Defensive extraction
    const slug = data.org_slug || data.slug || null
    const name = data.org_name || data.name || null
    const plan = data.org_plan || data.plan || null
    const role = data.org_role || 'candidate'
    // ❌ HARD STOP if slug missing
    if (!slug) {
      throw new Error('Organisation data missing from response')
    }
    // ✅ Safe storage
    setAuthData({
      org_slug: slug,
      org_role: role,
      org_name: name || 'Organisation',
      org_plan: plan || 'free'
    })

    router.push('/dashboard')
  } catch (error) {
    console.error('Failed to join organisation:', error)
    if (error.message === 'Organisation data missing from response') {
      errorMessage.value = 'Invalid invite response. Please try again.'
    } else if (error.response && error.response.data) {
      const errors = Object.values(error.response.data).flat()
      errorMessage.value = errors[0] || 'Invalid or expired invite code.'
    } else {
      errorMessage.value = 'A network error occurred. Please try again.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>