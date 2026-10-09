<template>
  <SimpleShell>
    <PageHeader title="Your organisation application" />
    <StateBlock :loading="loading" :error="loadError" :empty="!app" empty-title="No application yet" @retry="load">
      <template #empty-action><RouterLink :to="{ name: 'apply' }" class="btn-primary mt-2">Register an organisation</RouterLink></template>
      <div class="space-y-6">
        <div class="panel p-6">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p class="text-lg font-semibold">{{ app.name }}</p>
              <p class="text-sm text-neutral-500">Submitted {{ formatDate(app.submitted_at) }}</p>
            </div>
            <StatusBadge :status="app.status" :label="labels[app.status]" />
          </div>
          <p class="mt-4 text-sm text-neutral-700">{{ explanation }}</p>
          <div v-if="app.review_note" class="mt-4 rounded-md border border-neutral-200 bg-neutral-50 p-3 text-sm">
            <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Reviewer's note</p>
            <p class="mt-1 whitespace-pre-line">{{ app.review_note }}</p>
          </div>
          <div class="mt-4 flex gap-2">
            <button class="btn-secondary" @click="refresh">Check status</button>
            <RouterLink v-if="app.status === 'approved'" :to="{ name: 'home' }" class="btn-primary">Open dashboard</RouterLink>
          </div>
        </div>

        <div v-if="app.status === 'pending' || app.status === 'rejected'" class="panel p-6">
          <h2 class="mb-4 text-sm font-semibold">{{ app.status === 'rejected' ? 'Update and resubmit' : 'Edit application' }}</h2>
          <OrgDetailsForm v-model="form" :error="error" :busy="busy"
            :submit-label="app.status === 'rejected' ? 'Resubmit for review' : 'Save changes'" @submit="save" />
        </div>
      </div>
    </StateBlock>
  </SimpleShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import SimpleShell from '@/components/SimpleShell.vue'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import OrgDetailsForm from '@/components/OrgDetailsForm.vue'
import { applications } from '@/api/endpoints'
import { session } from '@/stores/session'
import { toast } from '@/stores/toast'
import { formatDate } from '@/format'

const router = useRouter()
const app = ref(null)
const loading = ref(true)
const loadError = ref(null)
const form = reactive({ name: '', description: '', contact_phone: '', website: '' })
const error = ref('')
const busy = ref(false)
const labels = { pending: 'Pending review', approved: 'Approved', rejected: 'Rejected', suspended: 'Suspended' }
const explanation = computed(() => ({
  pending: 'A platform administrator will review your application. You cannot invite members or create exams until it is approved.',
  approved: 'Your organisation is approved. Sign in again if the dashboard does not open.',
  rejected: 'This application was rejected. Read the note, update the details and resubmit it.',
  suspended: 'This organisation is suspended. Members cannot take exams until a platform administrator reactivates it.',
}[app.value?.status]))

async function load() {
  loading.value = true
  loadError.value = null
  try {
    const list = await applications.mine()
    app.value = list[0] || null
    if (app.value) Object.assign(form, {
      name: app.value.name, description: app.value.description,
      contact_phone: app.value.contact_phone, website: app.value.website,
    })
  } catch (e) {
    loadError.value = e
  } finally {
    loading.value = false
  }
}

async function refresh() {
  await session.load(true)
  if (session.adminOrgs().length) router.replace(session.homeRoute())
  else await load()
}

async function save() {
  busy.value = true
  error.value = ''
  try {
    app.value = app.value.status === 'rejected'
      ? await applications.resubmit(app.value.id, { ...form })
      : await applications.update(app.value.id, { ...form })
    toast.success(app.value.status === 'pending' ? 'Application saved' : 'Saved')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>
