<template>
  <PageHeader title="Platform overview" description="Organisations and activity across ParallaxLane." />
  <StateBlock :loading="loading" :error="error" @retry="load">
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatTile label="Pending review" :value="stats.organisations.pending" :to="{ name: 'platform-orgs', query: { status: 'pending' } }" />
      <StatTile label="Approved" :value="stats.organisations.approved" :to="{ name: 'platform-orgs', query: { status: 'approved' } }" />
      <StatTile label="Suspended" :value="stats.organisations.suspended" :to="{ name: 'platform-orgs', query: { status: 'suspended' } }" />
      <StatTile label="Rejected" :value="stats.organisations.rejected" :to="{ name: 'platform-orgs', query: { status: 'rejected' } }" />
      <StatTile label="Users" :value="stats.users" />
      <StatTile label="Exams" :value="stats.exams" />
      <StatTile label="Attempts, last 7 days" :value="stats.attempts_last_7_days" />
      <StatTile label="Exams in progress" :value="stats.active_attempts" />
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-3">
      <section class="panel lg:col-span-2">
        <div class="flex items-center justify-between border-b border-neutral-200 px-4 py-3">
          <h2 class="text-sm font-semibold">Waiting for review</h2>
          <RouterLink :to="{ name: 'platform-orgs', query: { status: 'pending' } }" class="text-xs link">View all</RouterLink>
        </div>
        <p v-if="!pending.length" class="px-4 py-8 text-center text-sm text-neutral-500">No applications are waiting.</p>
        <RouterLink v-for="o in pending" :key="o.id" :to="{ name: 'platform-org', params: { id: o.id } }"
          class="flex items-center justify-between border-b border-neutral-100 px-4 py-3 last:border-0 hover:bg-neutral-50">
          <div class="min-w-0">
            <p class="truncate text-sm font-medium">{{ o.name }}</p>
            <p class="truncate text-xs text-neutral-500">{{ o.owner.email }} · {{ formatDate(o.submitted_at) }}</p>
          </div>
          <ChevronRight class="h-4 w-4 shrink-0 text-neutral-400" />
        </RouterLink>
      </section>

      <section class="panel p-4">
        <h2 class="text-sm font-semibold">New applications</h2>
        <p class="mt-1 text-sm text-neutral-500">When closed, nobody can submit a new organisation application. Existing ones are unaffected.</p>
        <div class="mt-4 flex items-center justify-between">
          <StatusBadge :status="stats.organisation_creation_enabled ? 'open' : 'closed'" :label="stats.organisation_creation_enabled ? 'Open' : 'Closed'" />
          <button class="btn-secondary" :disabled="toggling" @click="toggleApplications">
            {{ stats.organisation_creation_enabled ? 'Close applications' : 'Open applications' }}
          </button>
        </div>
      </section>
    </div>
  </StateBlock>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ChevronRight } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatTile from '@/components/StatTile.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { platform } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { formatDate } from '@/format'

const stats = ref(null)
const pending = ref([])
const loading = ref(true)
const error = ref(null)
const toggling = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [s, p] = await Promise.all([platform.stats(), platform.organisations({ status: 'pending', ordering: 'oldest', page_size: 5 })])
    stats.value = s
    pending.value = p.results
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

async function toggleApplications() {
  toggling.value = true
  try {
    const res = await platform.setApplicationsOpen(!stats.value.organisation_creation_enabled)
    stats.value.organisation_creation_enabled = res.organisation_creation_enabled
    toast.success(res.organisation_creation_enabled ? 'Applications are open' : 'Applications are closed')
  } catch (e) {
    toast.error(e)
  } finally {
    toggling.value = false
  }
}

onMounted(load)
</script>
