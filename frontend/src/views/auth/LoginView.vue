<template>
  <AuthCard title="Sign in" description="Administration for ParallaxLane organisations.">
    <p v-if="session.state.expired" class="mb-4 rounded-md border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm">Your session ended. Sign in again.</p>
    <form class="space-y-4" novalidate @submit.prevent="submit">
      <div>
        <label class="label" for="email">Email</label>
        <input id="email" v-model="email" type="email" autocomplete="username" class="input" required />
      </div>
      <div>
        <label class="label" for="password">Password</label>
        <input id="password" v-model="password" type="password" autocomplete="current-password" class="input" required />
      </div>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <button type="submit" class="btn-primary w-full" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
    </form>
    <template #below>
      <RouterLink :to="{ name: 'register' }" class="link">Create an account</RouterLink>
      <span class="mx-2">·</span>
      <RouterLink :to="{ name: 'reset-password' }" class="link">Forgot password</RouterLink>
    </template>
  </AuthCard>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AuthCard from '@/components/AuthCard.vue'
import { session } from '@/stores/session'

const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  if (!email.value.trim() || !password.value) {
    error.value = 'Enter your email and password.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await session.login(email.value, password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : null
    router.replace(next || session.homeRoute())
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
