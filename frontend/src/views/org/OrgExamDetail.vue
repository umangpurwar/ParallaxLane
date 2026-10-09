<template>
  <StateBlock :loading="loading" :error="error" @retry="load">
    <PageHeader :title="exam.title" :back="{ name: 'org-exams', params: { slug } }" back-label="Exams"
      :description="`${formatDate(exam.start_time)} to ${formatDate(exam.end_time)} · ${exam.duration} min · ${exam.questions.length} questions`">
      <RouterLink :to="{ name: 'org-exam-edit', params: { slug, examId } }" class="btn-secondary">Edit</RouterLink>
      <button class="btn-primary" :disabled="exporting" @click="exportCsv"><Download class="h-4 w-4" />{{ exporting ? 'Preparing…' : 'Export CSV' }}</button>
    </PageHeader>

    <div class="mb-4 flex gap-1" role="tablist">
      <button v-for="t in tabs" :key="t.value" role="tab" :aria-selected="tab === t.value"
        class="rounded-md px-3 py-1.5 text-sm" :class="tab === t.value ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'"
        @click="tab = t.value">{{ t.label }}</button>
    </div>

    <section v-if="tab === 'live'" class="panel">
      <div class="flex items-center justify-between border-b border-neutral-200 px-4 py-3 text-sm">
        <span class="text-neutral-500">Refreshes every 10 seconds{{ liveUpdated ? ` · updated ${liveUpdated}` : '' }}</span>
        <button class="btn-ghost h-8" :disabled="liveLoading" @click="loadLive"><RefreshCw class="h-4 w-4" :class="liveLoading ? 'animate-spin' : ''" />Refresh</button>
      </div>
      <StateBlock :loading="liveLoading && !live" :error="liveError" :empty="live && !live.length" empty-title="Nobody has started yet" @retry="loadLive">
        <div class="overflow-x-auto">
          <table class="table">
            <thead><tr><th>Candidate</th><th>Status</th><th>Phone</th><th class="text-right">Warnings</th><th class="text-right">Risk</th><th>Last seen</th><th class="text-right"></th></tr></thead>
            <tbody>
              <tr v-for="r in live" :key="r.attempt_id">
                <td><p class="font-medium">{{ r.display_name || r.username }}</p><p class="text-xs text-neutral-500">{{ r.username }}</p></td>
                <td><StatusBadge :status="r.status" /><span v-if="r.end_reason" class="ml-1 text-xs text-neutral-500">{{ humanize(r.end_reason) }}</span></td>
                <td class="text-xs text-neutral-600">{{ phoneState(r.system_health) }}</td>
                <td class="text-right tabular-nums">{{ r.violations_count }}</td>
                <td class="text-right tabular-nums">{{ r.risk_score }}</td>
                <td class="whitespace-nowrap text-neutral-600">{{ formatDate(r.last_active) }}</td>
                <td class="text-right"><button v-if="r.violations_count" class="btn-secondary h-8" @click="clearTarget = r">Clear warnings</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </StateBlock>
    </section>

    <section v-else-if="tab === 'results'" class="panel">
      <StateBlock :loading="resultsLoading" :error="resultsError" :empty="results && !results.length" empty-title="No results yet" @retry="loadResults">
        <div class="overflow-x-auto">
          <table class="table">
            <thead><tr><th>Candidate</th><th>Status</th><th class="text-right">Score</th><th class="text-right">Warnings</th><th>Started</th><th>Finished</th></tr></thead>
            <tbody>
              <tr v-for="r in results" :key="r.username">
                <td><p class="font-medium">{{ r.name || r.email }}</p><p v-if="r.name" class="text-xs text-neutral-500">{{ r.email }}</p></td>
                <td><StatusBadge :status="r.status" /><span v-if="r.end_reason" class="ml-1 text-xs text-neutral-500">{{ humanize(r.end_reason) }}</span></td>
                <td class="text-right tabular-nums">{{ r.points_scored ?? '–' }} / {{ r.total_points ?? '–' }}</td>
                <td class="text-right tabular-nums">{{ r.violations }}</td>
                <td class="whitespace-nowrap text-neutral-600">{{ formatDate(r.start_time) }}</td>
                <td class="whitespace-nowrap text-neutral-600">{{ formatDate(r.end_time) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </StateBlock>
    </section>

    <section v-else class="panel divide-y divide-neutral-100">
      <div v-for="(q, i) in exam.questions" :key="q.id" class="p-4 text-sm">
        <p class="font-medium">{{ i + 1 }}. {{ q.text }} <span class="font-normal text-neutral-500">({{ q.points }} pts)</span></p>
        <ul v-if="q.options.length" class="mt-2 space-y-1">
          <li v-for="o in q.options" :key="o.id" :class="o.is_correct ? 'font-medium' : 'text-neutral-600'">{{ o.is_correct ? '✓' : '·' }} {{ o.text }}</li>
        </ul>
        <p v-else class="mt-2">Answer: <span class="font-medium">{{ q.correct_text_answer }}</span></p>
      </div>
    </section>
  </StateBlock>

  <ConfirmDialog :open="!!clearTarget" title="Clear warnings" :message="`Remove all recorded warnings for ${clearTarget?.username} in this exam? The action is kept in the audit log.`"
    confirm-label="Clear" danger :action="clearWarnings" @close="clearTarget = null" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Download, RefreshCw } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { exams as examApi } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { formatDate, humanize } from '@/format'

const route = useRoute()
const slug = route.params.slug
const examId = route.params.examId
const tabs = [{ value: 'live', label: 'Live' }, { value: 'results', label: 'Results' }, { value: 'questions', label: 'Questions' }]
const tab = ref('live')
const exam = ref(null)
const loading = ref(true)
const error = ref(null)
const live = ref(null)
const liveLoading = ref(false)
const liveError = ref(null)
const liveUpdated = ref('')
const results = ref(null)
const resultsLoading = ref(false)
const resultsError = ref(null)
const exporting = ref(false)
const clearTarget = ref(null)
let timer = null
let liveInFlight = false

function phoneState(h) {
  if (!h) return '–'
  const issues = []
  if (h.tab_focus === false) issues.push('left the app')
  if (h.fullscreen === false) issues.push('not pinned')
  if (h.multi_window) issues.push('split screen')
  if (h.overlay_suspect) issues.push('overlay')
  return issues.length ? issues.join(', ') : 'OK'
}

async function load() {
  loading.value = true
  error.value = null
  try {
    exam.value = await examApi.detail(examId)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

async function loadLive() {
  if (liveInFlight) return // never stack polls when the server is slow
  liveInFlight = true
  liveLoading.value = true
  try {
    live.value = await examApi.live(examId)
    liveError.value = null
    liveUpdated.value = new Date().toLocaleTimeString()
  } catch (e) {
    liveError.value = e
  } finally {
    liveInFlight = false
    liveLoading.value = false
  }
}

async function loadResults() {
  resultsLoading.value = true
  resultsError.value = null
  try {
    results.value = await examApi.results(examId)
  } catch (e) {
    resultsError.value = e
  } finally {
    resultsLoading.value = false
  }
}

function startPolling() {
  stopPolling()
  loadLive()
  timer = setInterval(() => { if (!document.hidden) loadLive() }, 10000)
}
function stopPolling() { if (timer) clearInterval(timer); timer = null }

watch(tab, (value) => {
  if (value === 'live') startPolling()
  else stopPolling()
  if (value === 'results') loadResults()
})

async function exportCsv() {
  exporting.value = true
  try {
    const blob = await examApi.exportCsv(examId)
    const url = URL.createObjectURL(blob)
    const link = Object.assign(document.createElement('a'), { href: url, download: `${exam.value.title.replace(/[^\w]+/g, '_')}_report.csv` })
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error(e)
  } finally {
    exporting.value = false
  }
}

async function clearWarnings() {
  try {
    await examApi.clearViolations(examId, clearTarget.value.username)
    toast.success('Warnings cleared')
    loadLive()
  } catch (e) {
    toast.error(e)
    throw e
  }
}

onMounted(async () => { await load(); if (exam.value) startPolling() })
onBeforeUnmount(stopPolling)
</script>
