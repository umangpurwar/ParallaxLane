<template>
  <AuthCard title="Reset password" :description="step === 1 ? 'We will email you a 6 digit code.' : `Enter the code sent to ${email}.`">
    <form v-if="step === 1" class="space-y-4" novalidate @submit.prevent="sendCode">
      <div>
        <label class="label" for="email">Email</label>
        <input id="email" v-model="email" type="email" autocomplete="email" class="input" />
      </div>
      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <button type="submit" class="btn-primary w-full" :disabled="busy">{{ busy ? 'Sending…' : 'Send code' }}</button>
    </form>
    <form v-else-if="step === 2" class="space-y-4" novalidate @submit.prevent="reset">
      <div>
        <label class="label" for="otp">Code</label>
        <input id="otp" v-model="otp" inputmode="numeric" maxlength="6" class="input font-mono tracking-widest" />
      </div>
      <div>
        <label class="label" for="password">New password</label>
        <input id="password" v-model="password" type="password" autocomplete="new-password" class="input" />
      </div>
      <p v-if="error" class="field-error whitespace-pre-line" role="alert">{{ error }}</p>
      <button type="submit" class="btn-primary w-full" :disabled="busy">{{ busy ? 'Saving…' : 'Set new password' }}</button>
    </form>
    <p v-else class="text-sm">Your password was changed. All other sessions were signed out.</p>
    <template #below><RouterLink :to="{ name: 'login' }" class="link">Back to sign in</RouterLink></template>
  </AuthCard>
</template>

<script setup>
import { ref } from 'vue'
import AuthCard from '@/components/AuthCard.vue'
import { auth } from '@/api/endpoints'

const step = ref(1)
const email = ref('')
const otp = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function sendCode() {
  busy.value = true
  error.value = ''
  try {
    email.value = email.value.trim().toLowerCase()
    await auth.sendOtp(email.value, 'forgot')
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function reset() {
  busy.value = true
  error.value = ''
  try {
    await auth.verifyForgot({ email: email.value, otp: otp.value, password: password.value })
    step.value = 3
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>
