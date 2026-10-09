<template>
  <PageHeader title="Organisations" description="Review applications and manage organisation access." />
  <div class="panel">
    <div class="flex flex-col gap-3 border-b border-neutral-200 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex flex-wrap gap-1" role="tablist">
        <button v-for="tab in tabs" :key="tab.value" role="tab" :aria-selected="status === tab.value"
          class="rounded-md px-3 py-1.5 text-sm" :class="status === tab.value ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'"
          @click="setStatus(tab.value)">{{ tab.label }}</button>
      </div>
      <div class="flex gap-2">
        <input v-model="search" type="search" class="input sm:w-56" placeholder="Search name or owner email" aria-label="Search" />
        <select v-model="ordering" class="input w-auto" aria-label="Sort" @change="load(1)">
          <option value="newest">Newest</option><option value="oldest">Oldest</option><option value="name">Name</option>
        </select>
      </div>
    </div>
    <StateBlock :loading="loading" :error="error" :empty="!data?.results.length" empty-title="No organisations match" @retry="load(page)">
      <div class="overflow-x-auto">
        <table class="table">
          <thead><tr><th>Organisation</th><th>Owner</th><th>Status</th><th class="text-right">Members</th><th class="text-right">Exams</th><th>Submitted</th></tr></thead>
          <tbody>
            <tr v-for="o in data.results" :key="o.id" class="cursor-pointer" @click="$router.push({ name: 'platform-org', params: { id: o.id } })">
              <td><RouterLink :to="{ name: 'platform-org', params: { id: o.id } }" class="font-medium hover:underline" @click.stop>{{ o.name }}</RouterLink></td>
              <td class="text-neutral-600">{{ o.owner.email }}</td>
              <td><StatusBadge :status="o.status" /></td>
              <td class="text-right tabular-nums">{{ o.member_count }}</td>
              <td class="text-right tabular-nums">{{ o.exam_count }}</td>
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(o.submitted_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pager :data="data" @page="load" />
    </StateBlock>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Pager from '@/components/Pager.vue'
import { platform } from '@/api/endpoints'
import { formatDate } from '@/format'

const route = useRoute()
const router = useRouter()
const tabs = [
  { value: '', label: 'All' }, { value: 'pending', label: 'Pending' }, { value: 'approved', label: 'Approved' },
  { value: 'suspended', label: 'Suspended' }, { value: 'rejected', label: 'Rejected' },
]
const status = ref(route.query.status || '')
const search = ref('')
const ordering = ref('newest')
const data = ref(null)
const page = ref(1)
const loading = ref(true)
const error = ref(null)
let requestId = 0
let timer = null

async function load(p = 1) {
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    const result = await platform.organisations({ status: status.value || undefined, search: search.value || undefined, ordering: ordering.value, page: p })
    if (id !== requestId) return // a newer search already replaced this one
    data.value = result
    page.value = result.page
  } catch (e) {
    if (id === requestId) error.value = e
  } finally {
    if (id === requestId) loading.value = false
  }
}

function setStatus(value) {
  status.value = value
  router.replace({ query: value ? { status: value } : {} })
  load(1)
}

watch(search, () => { clearTimeout(timer); timer = setTimeout(() => load(1), 300) })
onBeforeUnmount(() => clearTimeout(timer))
onMounted(() => load(1))
</script>
