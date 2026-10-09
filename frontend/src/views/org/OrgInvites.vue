<template>
  <PageHeader title="Invitations" description="Invited people join from the ParallaxLane app after signing in with the invited email." />

  <form class="panel mb-6 grid gap-3 p-4 sm:grid-cols-[1fr_10rem_8rem_auto] sm:items-end" novalidate @submit.prevent="send">
    <div>
      <label class="label" for="invite-email">Email</label>
      <input id="invite-email" v-model="form.email" type="email" class="input" placeholder="student@college.edu" />
    </div>
    <div>
      <label class="label" for="invite-role">Role</label>
      <select id="invite-role" v-model="form.role" class="input">
        <option value="candidate">Candidate</option><option value="invigilator">Invigilator</option><option value="admin">Admin</option>
      </select>
    </div>
    <div>
      <label class="label" for="invite-days">Expires in</label>
      <select id="invite-days" v-model.number="form.expiry_days" class="input">
        <option :value="1">1 day</option><option :value="7">7 days</option><option :value="30">30 days</option>
      </select>
    </div>
    <button type="submit" class="btn-primary" :disabled="sending">{{ sending ? 'Sending…' : 'Send invite' }}</button>
    <p v-if="formError" class="field-error sm:col-span-4" role="alert">{{ formError }}</p>
  </form>

  <div class="panel">
    <div class="flex flex-col gap-2 border-b border-neutral-200 p-3 sm:flex-row">
      <input v-model="search" type="search" class="input sm:w-64" placeholder="Search email" aria-label="Search invitations" />
      <select v-model="status" class="input sm:w-40" aria-label="Filter by status" @change="load(1)">
        <option value="">All</option><option value="pending">Pending</option><option value="accepted">Accepted</option>
        <option value="declined">Declined</option><option value="revoked">Revoked</option><option value="expired">Expired</option>
      </select>
    </div>
    <StateBlock :loading="loading" :error="error" :empty="!data?.results.length" empty-title="No invitations" @retry="load(page)">
      <div class="overflow-x-auto">
        <table class="table">
          <thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Sent</th><th>Expires</th><th class="text-right"></th></tr></thead>
          <tbody>
            <tr v-for="i in data.results" :key="i.id">
              <td class="font-medium">{{ i.email }}</td>
              <td class="capitalize">{{ i.role }}</td>
              <td><StatusBadge :status="i.status" /></td>
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(i.created_at) }}</td>
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(i.expires_at) }}</td>
              <td class="text-right"><button v-if="i.status === 'pending'" class="btn-danger h-8" @click="revokeTarget = i">Revoke</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pager :data="data" @page="load" />
    </StateBlock>
  </div>

  <ConfirmDialog :open="!!revokeTarget" title="Revoke invitation" :message="`${revokeTarget?.email} will no longer be able to join with this invitation.`"
    confirm-label="Revoke" danger :action="revoke" @close="revokeTarget = null" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import Pager from '@/components/Pager.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { org } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { formatDate } from '@/format'

const slug = useRoute().params.slug
const form = reactive({ email: '', role: 'candidate', expiry_days: 7 })
const formError = ref('')
const sending = ref(false)
const data = ref(null)
const page = ref(1)
const loading = ref(true)
const error = ref(null)
const status = ref('')
const search = ref('')
const revokeTarget = ref(null)
let requestId = 0
let timer = null

async function load(p = 1) {
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    const result = await org.invites(slug, { page: p, status: status.value || undefined, search: search.value || undefined })
    if (id !== requestId) return
    data.value = result
    page.value = result.page
  } catch (e) {
    if (id === requestId) error.value = e
  } finally {
    if (id === requestId) loading.value = false
  }
}

async function send() {
  const email = form.email.trim().toLowerCase()
  if (!/^\S+@\S+\.\S+$/.test(email)) { formError.value = 'Enter a valid email address.'; return }
  sending.value = true
  formError.value = ''
  try {
    const res = await org.invite(slug, { ...form, email })
    toast.success(res.status === 'invite already exists' ? 'A pending invitation already exists for this email' : `Invitation sent to ${email}`)
    form.email = ''
    load(1)
  } catch (e) {
    formError.value = e.message
  } finally {
    sending.value = false
  }
}

async function revoke() {
  try {
    await org.revokeInvite(slug, revokeTarget.value.id)
    toast.success('Invitation revoked')
    load(page.value)
  } catch (e) {
    toast.error(e)
    throw e
  }
}

watch(search, () => { clearTimeout(timer); timer = setTimeout(() => load(1), 300) })
onBeforeUnmount(() => clearTimeout(timer))
onMounted(() => load(1))
</script>
