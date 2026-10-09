<template>
  <AuthCard title="Create an account" :description="step === 1 ? 'We will email you a 6 digit code.' : `Enter the code sent to ${email}.`">
    <form v-if="step === 1" class="space-y-4" novalidate @submit.prevent="sendCode">
      <div>
        <label class="label" for="email">Email</label>
        <input id="email" v-model="email" type="email" autocomplete="email" class="input" />
      </div>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <button type="submit" class="btn-primary w-full" :disabled="busy">{{ busy ? 'Sending…' : 'Send code' }}</button>
    </form>

    <form v-else class="space-y-4" novalidate @submit.prevent="verify">
      <div>
        <label class="label" for="otp">Code</label>
        <input id="otp" v-model="otp" inputmode="numeric" maxlength="6" autocomplete="one-time-code" class="input font-mono tracking-widest" />
      </div>
      <div>
        <label class="label" for="name">Full name</label>
        <input id="name" v-model="name" autocomplete="name" class="input" />
      </div>
      <div>
        <label class="label" for="password">Password</label>
        <input id="password" v-model="password" type="password" autocomplete="new-password" class="input" />
        <p class="help">At least 8 characters, not only numbers.</p>
      </div>
      <p v-if="error" class="field-error whitespace-pre-line" role="alert">{{ error }}</p>
      <button type="submit" class="btn-primary w-full" :disabled="busy">{{ busy ? 'Creating…' : 'Create account' }}</button>
      <button type="button" class="btn-ghost w-full" :disabled="busy" @click="step = 1">Use a different email</button>
    </form>
    <template #below>Already registered? <RouterLink :to="{ name: 'login' }" class="link">Sign in</RouterLink></template>
  </AuthCard>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AuthCard from '@/components/AuthCard.vue'
import { auth } from '@/api/endpoints'
import { tokens } from '@/api/client'
import { session } from '@/stores/session'

const router = useRouter()
const step = ref(1)
const email = ref('')
const otp = ref('')
const name = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function sendCode() {
  const value = email.value.trim().toLowerCase()
  if (!/^\S+@\S+\.\S+$/.test(value)) { error.value = 'Enter a valid email address.'; return }
  busy.value = true
  error.value = ''
  try {
    await auth.sendOtp(value, 'register')
    email.value = value
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function verify() {
  if (!/^\d{6}$/.test(otp.value) || !name.value.trim() || !password.value) {
    error.value = 'Enter the 6 digit code, your name and a password.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const data = await auth.verifyRegister({ email: email.value, otp: otp.value, name: name.value.trim(), password: password.value })
    tokens.set(data.access, data.refresh)
    await session.load(true)
    router.replace(session.homeRoute())
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
