<template>
  <PageHeader title="Members" description="People who joined through an invitation or the join code.">
    <RouterLink :to="{ name: 'org-invites', params: { slug } }" class="btn-primary"><UserPlus class="h-4 w-4" />Invite</RouterLink>
  </PageHeader>
  <div class="panel">
    <div class="flex flex-col gap-2 border-b border-neutral-200 p-3 sm:flex-row">
      <input v-model="search" type="search" class="input sm:w-64" placeholder="Search name or email" aria-label="Search members" />
      <select v-model="role" class="input sm:w-44" aria-label="Filter by role">
        <option value="">All roles</option><option value="owner">Owner</option><option value="admin">Admin</option>
        <option value="invigilator">Invigilator</option><option value="candidate">Candidate</option>
      </select>
    </div>
    <StateBlock :loading="loading" :error="error" :empty="!filtered.length" empty-title="No members found" @retry="load">
      <div class="overflow-x-auto">
        <table class="table">
          <thead><tr><th>Member</th><th>Role</th><th>Status</th><th>Exam access</th><th>Joined</th><th class="text-right">Actions</th></tr></thead>
          <tbody>
            <tr v-for="m in filtered" :key="m.id">
              <td><p class="font-medium">{{ m.name || m.email }}</p><p v-if="m.name" class="text-xs text-neutral-500">{{ m.email }}</p></td>
              <td class="capitalize">{{ m.role }}</td>
              <td><StatusBadge :status="m.is_active ? 'active' : 'inactive'" /></td>
              <td>{{ m.is_exam_enabled ? 'Allowed' : 'Blocked' }}</td>
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(m.joined_at) }}</td>
              <td class="text-right">
                <div v-if="m.role !== 'owner' && m.email !== myEmail" class="flex justify-end gap-2">
                  <button class="btn-secondary h-8" :disabled="busyId === m.id" @click="toggleExam(m)">{{ m.is_exam_enabled ? 'Block exams' : 'Allow exams' }}</button>
                  <button class="btn-danger h-8" :disabled="busyId === m.id" @click="confirmTarget = m">{{ m.is_active ? 'Deactivate' : 'Reactivate' }}</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </StateBlock>
  </div>
  <ConfirmDialog :open="!!confirmTarget" :title="confirmTarget?.is_active ? 'Deactivate member' : 'Reactivate member'"
    :message="confirmTarget?.is_active ? `${confirmTarget?.email} will lose access to this organisation and its exams.` : `${confirmTarget?.email} will regain access.`"
    :confirm-label="confirmTarget?.is_active ? 'Deactivate' : 'Reactivate'" :danger="confirmTarget?.is_active" :action="setActive" @close="confirmTarget = null" />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { UserPlus } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { org } from '@/api/endpoints'
import { session } from '@/stores/session'
import { toast } from '@/stores/toast'
import { formatDate } from '@/format'

const route = useRoute()
const slug = route.params.slug
const myEmail = session.state.me?.email
const members = ref([])
const loading = ref(true)
const error = ref(null)
const search = ref('')
const role = ref('')
const busyId = ref(null)
const confirmTarget = ref(null)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return members.value.filter((m) => (!role.value || m.role === role.value)
    && (!q || m.email.toLowerCase().includes(q) || (m.name || '').toLowerCase().includes(q)))
})

async function load() {
  loading.value = true
  error.value = null
  try {
    members.value = await org.members(slug)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

async function toggleExam(m) {
  busyId.value = m.id
  try {
    const res = await org.setExamAccess(slug, m.id, !m.is_exam_enabled)
    m.is_exam_enabled = res.is_exam_enabled
    toast.success(m.is_exam_enabled ? 'Exam access allowed' : 'Exam access blocked')
  } catch (e) {
    toast.error(e)
  } finally {
    busyId.value = null
  }
}

async function setActive() {
  const m = confirmTarget.value
  try {
    const res = await org.setMemberActive(slug, m.id, !m.is_active)
    m.is_active = res.is_active
    toast.success(m.is_active ? 'Member reactivated' : 'Member deactivated')
  } catch (e) {
    toast.error(e)
    throw e
  }
}

onMounted(load)
</script>
