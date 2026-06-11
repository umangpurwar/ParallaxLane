<template>
  <div class="min-h-screen bg-brutal-paper font-sans text-brutal-ink">
    <header class="h-20 flex items-center justify-between px-8 border-b border-brutal-border bg-brutal-paper">
      <div class="flex items-center gap-4">
        <button
          @click="goBack"
          class="text-[9px] uppercase tracking-widest font-bold text-gray-500 hover:text-brutal-ink"
        >
          ← Back
        </button>
        <div>
          <h1 class="text-2xl font-medium tracking-tight">Organisation Settings</h1>
          <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500 mt-1">
            Plan &amp; usage
          </p>
        </div>
      </div>
      <PlanBadge v-if="settings.plan" :plan="settings.plan" />
    </header>

    <main class="max-w-3xl mx-auto p-8 space-y-8">
      <div v-if="isLoading" class="text-sm text-gray-500">Loading settings...</div>

      <template v-else>
        <section class="bg-white border border-brutal-border p-6 md:p-8">
          <h2 class="text-lg font-medium tracking-tight mb-1">{{ settings.organisation?.name }}</h2>
          <p class="text-[9px] uppercase tracking-widest text-gray-500 mb-6">
            {{ settings.organisation?.slug }}
          </p>

          <div class="flex items-center gap-3 mb-6">
            <span class="text-[9px] uppercase tracking-widest font-bold text-gray-500">Current Plan</span>
            <PlanBadge :plan="settings.plan" />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div class="border border-brutal-border/50 p-4">
              <p class="text-[9px] uppercase tracking-widest font-bold text-gray-500 mb-1">Exams</p>
              <p class="text-xl font-medium">
                {{ settings.usage?.exams_created ?? 0 }}
                <span class="text-sm text-gray-500">/ {{ settings.usage?.max_exams ?? '—' }}</span>
              </p>
            </div>
            <div class="border border-brutal-border/50 p-4">
              <p class="text-[9px] uppercase tracking-widest font-bold text-gray-500 mb-1">Candidates</p>
              <p class="text-xl font-medium">
                {{ settings.usage?.candidates ?? 0 }}
                <span class="text-sm text-gray-500">/ {{ settings.usage?.max_candidates ?? '—' }}</span>
              </p>
            </div>
            <div class="border border-brutal-border/50 p-4">
              <p class="text-[9px] uppercase tracking-widest font-bold text-gray-500 mb-1">Questions / Exam</p>
              <p class="text-xl font-medium">{{ settings.features?.max_questions_per_exam ?? '—' }}</p>
            </div>
            <div class="border border-brutal-border/50 p-4">
              <p class="text-[9px] uppercase tracking-widest font-bold text-gray-500 mb-1">Question Types</p>
              <p class="text-xs uppercase tracking-wide text-brutal-ink">
                {{ (settings.features?.allowed_question_types || []).join(', ') || '—' }}
              </p>
            </div>
          </div>

          <div class="mt-4 flex flex-wrap gap-2 text-[9px] uppercase tracking-widest font-bold">
            <span
              class="px-2 py-1 border"
              :class="settings.features?.image_questions ? 'border-green-600 text-green-700' : 'border-gray-300 text-gray-400'"
            >
              Image Questions {{ settings.features?.image_questions ? 'ON' : 'OFF' }}
            </span>
            <span
              class="px-2 py-1 border"
              :class="settings.features?.file_upload ? 'border-green-600 text-green-700' : 'border-gray-300 text-gray-400'"
            >
              File Upload {{ settings.features?.file_upload ? 'ON' : 'OFF' }}
            </span>
            <span
              class="px-2 py-1 border"
              :class="settings.usage?.proctoring_enabled ? 'border-green-600 text-green-700' : 'border-gray-300 text-gray-400'"
            >
              Proctoring {{ settings.usage?.proctoring_enabled ? 'ON' : 'OFF' }}
            </span>
          </div>
        </section>

        <section
          v-if="settings.can_redeem_coupons"
          class="bg-white border border-brutal-border p-6 md:p-8"
        >
          <h2 class="text-lg font-medium tracking-tight mb-2">Upgrade with Coupon</h2>
          <p class="text-sm text-gray-600 mb-6">
            Enter a coupon code to upgrade your organisation plan. No payment gateway required.
          </p>

          <form @submit.prevent="redeemCoupon" class="flex flex-col sm:flex-row gap-3">
            <input
              v-model="couponCode"
              type="text"
              placeholder="ENTER COUPON CODE"
              class="flex-1 border-2 border-brutal-ink px-4 py-3 text-sm font-bold uppercase tracking-wide outline-none focus:ring-2 focus:ring-brutal-red"
              :disabled="isRedeeming"
            />
            <button
              type="submit"
              :disabled="isRedeeming || !couponCode.trim()"
              class="px-6 py-3 bg-brutal-ink text-white text-[9px] uppercase tracking-widest font-bold hover:bg-brutal-red transition-colors disabled:opacity-50"
            >
              {{ isRedeeming ? 'Redeeming...' : 'Redeem Coupon' }}
            </button>
          </form>

          <p v-if="successMessage" class="mt-4 text-sm font-medium text-green-700">{{ successMessage }}</p>
          <p v-if="errorMessage" class="mt-4 text-sm font-medium text-brutal-red">{{ errorMessage }}</p>
        </section>

        <section v-else class="bg-white border border-brutal-border p-6 text-sm text-gray-600">
          Only organisation owners and admins can redeem coupon codes.
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { setOrgContext, STAFF_ROLES } from '@/services/api'
import PlanBadge from '@/components/PlanBadge.vue'

const router = useRouter()

const settings = ref({})
const isLoading = ref(true)
const couponCode = ref('')
const isRedeeming = ref(false)
const successMessage = ref('')
const errorMessage = ref('')

const fetchSettings = async () => {
  isLoading.value = true
  try {
    const res = await api.get('organisations/settings/')
    settings.value = res.data
    if (res.data.plan) {
      localStorage.setItem('org_plan', res.data.plan)
    }
  } catch (err) {
    console.error('Failed to load settings', err)
    errorMessage.value = err.response?.data?.error || 'Could not load organisation settings.'
  } finally {
    isLoading.value = false
  }
}

const redeemCoupon = async () => {
  isRedeeming.value = true
  successMessage.value = ''
  errorMessage.value = ''

  try {
    const res = await api.post('organisations/redeem-coupon/', {
      code: couponCode.value.trim(),
    })

    setOrgContext(res.data)
    successMessage.value = res.data.message || 'Plan upgraded successfully.'
    couponCode.value = ''
    settings.value = { ...settings.value, ...res.data, organisation: settings.value.organisation }
    await fetchSettings()
  } catch (err) {
    errorMessage.value = err.response?.data?.error || 'Failed to redeem coupon.'
  } finally {
    isRedeeming.value = false
  }
}

const goBack = () => {
  const role = localStorage.getItem('org_role')
  if (STAFF_ROLES.includes(role)) {
    router.push('/admin')
  } else {
    router.push('/org-home')
  }
}

onMounted(fetchSettings)
</script>
