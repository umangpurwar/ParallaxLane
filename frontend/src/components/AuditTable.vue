<template>
  <div class="panel">
    <div class="border-b border-neutral-200 p-3">
      <input v-model="search" type="search" class="input sm:w-72" :placeholder="searchPlaceholder" aria-label="Search" />
    </div>
    <StateBlock :loading="loading" :error="error" :empty="!data?.results.length" empty-title="No activity recorded" @retry="load(page)">
      <div class="overflow-x-auto">
        <table class="table">
          <thead><tr><th>When</th><th>Action</th><th>By</th><th v-if="showOrg">Organisation</th><th>Details</th></tr></thead>
          <tbody>
            <tr v-for="e in data.results" :key="e.id">
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(e.created_at) }}</td>
              <td class="font-medium">{{ humanize(e.action) }}</td>
              <td class="text-neutral-600">{{ e.actor || 'system' }}</td>
              <td v-if="showOrg" class="text-neutral-600">{{ e.organisation?.name || '–' }}</td>
              <td class="max-w-xs truncate text-neutral-600" :title="details(e)">{{ details(e) }}</td>
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
import StateBlock from './StateBlock.vue'
import Pager from './Pager.vue'
import { formatDate, humanize } from '@/format'

const props = defineProps({ fetcher: Function, showOrg: Boolean, searchPlaceholder: { type: String, default: 'Search' } })
const data = ref(null)
const page = ref(1)
const loading = ref(true)
const error = ref(null)
const search = ref('')
let requestId = 0
let timer = null

function details(e) {
  const parts = [e.target, ...Object.entries(e.metadata || {}).filter(([, v]) => v !== '' && v !== null).map(([k, v]) => `${humanize(k)}: ${v}`)]
  return parts.filter(Boolean).join(' · ')
}

async function load(p = 1) {
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    const result = await props.fetcher({ page: p, search: search.value || undefined })
    if (id !== requestId) return
    data.value = result
    page.value = result.page
  } catch (e) {
    if (id === requestId) error.value = e
  } finally {
    if (id === requestId) loading.value = false
  }
}

watch(search, () => { clearTimeout(timer); timer = setTimeout(() => load(1), 300) })
onBeforeUnmount(() => clearTimeout(timer))
onMounted(() => load(1))
</script>
