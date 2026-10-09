<template>
  <PageHeader title="Exams" description="Candidates see published exams in the app while they are open.">
    <RouterLink :to="{ name: 'org-exam-new', params: { slug } }" class="btn-primary"><Plus class="h-4 w-4" />New exam</RouterLink>
  </PageHeader>
  <div class="panel">
    <StateBlock :loading="loading" :error="error" :empty="!exams.length" empty-title="No exams yet" empty-text="Create an exam, add questions and publish it when it is ready." @retry="load">
      <div class="overflow-x-auto">
        <table class="table">
          <thead><tr><th>Exam</th><th>Window</th><th>Duration</th><th>State</th><th class="text-right">Actions</th></tr></thead>
          <tbody>
            <tr v-for="e in exams" :key="e.id">
              <td>
                <RouterLink :to="{ name: 'org-exam', params: { slug, examId: e.id } }" class="font-medium hover:underline">{{ e.title }}</RouterLink>
                <p class="text-xs text-neutral-500">{{ e.questions.length }} questions</p>
              </td>
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(e.start_time) }}<br />{{ formatDate(e.end_time) }}</td>
              <td class="tabular-nums">{{ e.duration }} min</td>
              <td class="space-x-1 whitespace-nowrap">
                <StatusBadge :status="e.is_published ? 'published' : 'draft'" :label="e.is_published ? 'Published' : 'Draft'" />
                <StatusBadge :status="e.is_active ? 'active' : 'disabled'" :label="e.is_active ? 'Enabled' : 'Disabled'" />
              </td>
              <td class="text-right">
                <div class="flex justify-end gap-2">
                  <RouterLink :to="{ name: 'org-exam-edit', params: { slug, examId: e.id } }" class="btn-secondary h-8">Edit</RouterLink>
                  <button class="btn-secondary h-8" :disabled="busyId === e.id" @click="e.is_active ? (toggleTarget = e) : toggle(e)">{{ e.is_active ? 'Disable' : 'Enable' }}</button>
                  <button class="btn-danger h-8" @click="deleteTarget = e">Delete</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </StateBlock>
  </div>
  <ConfirmDialog :open="!!deleteTarget" title="Delete exam" :message="`Delete “${deleteTarget?.title}”? Exams that have attempts cannot be deleted; disable them instead.`"
    confirm-label="Delete" danger :action="remove" @close="deleteTarget = null" />
  <ConfirmDialog :open="!!toggleTarget" title="Disable exam" message="Disabling ends every running attempt of this exam and grades the answers saved so far."
    confirm-label="Disable" danger :action="() => toggle(toggleTarget)" @close="toggleTarget = null" />
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Plus } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { exams as examApi } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { formatDate } from '@/format'

const slug = useRoute().params.slug
const exams = ref([])
const loading = ref(true)
const error = ref(null)
const busyId = ref(null)
const deleteTarget = ref(null)
const toggleTarget = ref(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    exams.value = await examApi.list()
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

async function toggle(e) {
  busyId.value = e.id
  try {
    const res = await examApi.toggle(e.id)
    e.is_active = res.is_active
    toast.success(e.is_active ? 'Exam enabled' : 'Exam disabled')
  } catch (err) {
    toast.error(err)
  } finally {
    busyId.value = null
  }
}

async function remove() {
  try {
    await examApi.remove(deleteTarget.value.id)
    toast.success('Exam deleted')
    await load()
  } catch (e) {
    toast.error(e)
    throw e
  }
}

onMounted(load)
</script>
