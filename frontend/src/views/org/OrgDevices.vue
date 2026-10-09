<template>
  <PageHeader title="Phone approvals" description="A member's first phone is approved automatically. A new or shared phone needs your approval before it can be used for exams." />
  <div class="mb-3 flex gap-1" role="tablist">
    <button v-for="tab in tabs" :key="tab" role="tab" :aria-selected="status === tab"
      class="rounded-md px-3 py-1.5 text-sm capitalize" :class="status === tab ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'"
      @click="status = tab; load()">{{ tab }}</button>
  </div>
  <div class="panel">
    <StateBlock :loading="loading" :error="error" :empty="!devices.length" :empty-title="status === 'pending' ? 'No phones waiting' : 'No phones'" @retry="load">
      <div class="overflow-x-auto">
        <table class="table">
          <thead><tr><th>Member</th><th>Phone</th><th>Reason</th><th>Requested</th><th>Last seen</th><th class="text-right"></th></tr></thead>
          <tbody>
            <tr v-for="d in devices" :key="d.id">
              <td><p class="font-medium">{{ d.user_name || d.user_email }}</p><p class="text-xs text-neutral-500">{{ d.user_email }}</p></td>
              <td><p>{{ d.model_name || 'Unknown model' }}</p><p class="font-mono text-xs text-neutral-500">{{ d.device_id.slice(0, 16) }}</p></td>
              <td>{{ reasons[d.pending_reason] || '–' }}</td>
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(d.created_at) }}</td>
              <td class="whitespace-nowrap text-neutral-600">{{ formatDate(d.last_seen) }}</td>
              <td class="text-right">
                <div class="flex justify-end gap-2">
                  <button v-if="d.status === 'pending'" class="btn-primary h-8" :disabled="busyId === d.id" @click="decide(d, 'approve')">Approve</button>
                  <button v-if="d.status !== 'revoked'" class="btn-danger h-8" :disabled="busyId === d.id" @click="decide(d, 'revoke')">{{ d.status === 'pending' ? 'Reject' : 'Revoke' }}</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </StateBlock>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { org } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { formatDate } from '@/format'

const slug = useRoute().params.slug
const tabs = ['pending', 'approved', 'revoked']
const reasons = { device_change: 'New phone for this account', shared_device: 'Phone already used by another account' }
const status = ref('pending')
const devices = ref([])
const loading = ref(true)
const error = ref(null)
const busyId = ref(null)

async function load() {
  loading.value = true
  error.value = null
  try {
    devices.value = await org.devices(slug, status.value)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

async function decide(device, decision) {
  busyId.value = device.id
  try {
    await org.decideDevice(slug, device.id, decision)
    toast.success(decision === 'approve' ? 'Phone approved. The member\'s previous phone was revoked.' : 'Phone revoked')
    await load()
  } catch (e) {
    toast.error(e)
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>
