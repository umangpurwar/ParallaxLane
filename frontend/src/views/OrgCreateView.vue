<template>
  <div class="flex items-center justify-center h-screen bg-brutal-dark font-sans p-6 overflow-hidden relative">
    
    <div class="absolute inset-0 pointer-events-none z-0">
      <div class="grid-line-v left-[33%]"></div>
      <div class="grid-line-v left-[66%]"></div>
    </div>

    <div class="relative z-10 max-w-md w-full bg-brutal-paper text-brutal-ink border-4 border-brutal-ink p-10 flex flex-col shadow-[12px_12px_0px_0px_rgba(239,63,35,1)]">
      
      <h1 class="text-4xl font-black tracking-tighter text-brutal-ink mb-2 uppercase italic">
        Create Organisation
      </h1>
      <p class="text-[10px] uppercase tracking-widest font-bold text-gray-500 mb-8 border-b-2 border-brutal-ink pb-4">
        Establish your command center
      </p>

      <form @submit.prevent="createOrg" class="flex flex-col gap-6">
        <div class="relative">
          <input
            v-model="name"
            type="text"
            placeholder="ORGANISATION NAME"
            class="w-full bg-white border-2 border-brutal-border py-4 px-4 text-center text-brutal-ink font-bold tracking-[0.15em] uppercase placeholder-gray-400 focus:outline-none focus:border-brutal-ink transition-colors"
            :disabled="isSubmitting"
          />
        </div>

        <p v-if="errorMessage" class="text-[10px] uppercase tracking-widest font-bold text-brutal-red text-center leading-tight">
          {{ errorMessage }}
        </p>

        <button
          type="submit"
          :disabled="isSubmitting || !name.trim()"
          class="w-full py-5 text-[11px] uppercase tracking-[0.4em] font-black transition-all transform active:scale-95 border-b-4 border-r-4 border-gray-600"
          :class="(isSubmitting || !name.trim()) ? 'bg-gray-300 text-gray-500 cursor-not-allowed border-transparent' : 'bg-brutal-ink text-white hover:bg-brutal-red hover:border-brutal-ink cursor-pointer'"
        >
          {{ isSubmitting ? 'Creating...' : 'Create Organisation' }}
        </button>
      </form>

      <div class="mt-8 text-center">
        <router-link to="/join-org" class="text-[9px] uppercase tracking-widest font-bold text-gray-500 hover:text-brutal-red transition-colors">
          Have an invite code? Join an organisation
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

const name = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

onMounted(() => {
  const orgSlug = localStorage.getItem("org_slug")
  if (orgSlug) {
    router.push('/dashboard')
  }
})

const createOrg = async () => {
  errorMessage.value = ''

  if (!name.value.trim()) {
    errorMessage.value = 'Please enter an organisation name.'
    return
  }

  isSubmitting.value = true

  try {
    const response = await api.post('organisations/create/', {
      name: name.value.trim()
    })

    const data = response.data

    // 1. Safely extract values using the fallback pattern
    const slug = data.slug || data.org
    const orgName = data.name
    const plan = data.plan

    // 2. Strict validation to prevent writing undefined values
    if (!slug) {
      throw new Error('Organisation identifier missing from response.')
    }

    // 3. Save only valid values to localStorage
    setAuthData({
      org_slug: slug,
      org_role: 'owner',
      org_name: orgName || name.value.trim(), // Optional fallback to input name
      org_plan: plan || 'free'                // Optional fallback plan
    })

    router.push('/dashboard')
  } catch (error) {
    console.error('Failed to create organisation:', error)
    
    if (error.response && error.response.data) {
      const errors = Object.values(error.response.data).flat()
      errorMessage.value = errors[0] || 'Failed to create organisation.'
    } else if (error.message === 'Organisation identifier missing from response.') {
      errorMessage.value = 'Invalid server response. Please try again.'
    } else {
      errorMessage.value = 'A network error occurred. Please try again.'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>