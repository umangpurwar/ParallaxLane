<template>
  <StateBlock :loading="loading" :error="error" @retry="load">
    <PageHeader :title="org.name" :back="{ name: 'platform-orgs' }" back-label="Organisations">
      <template v-for="a in actions" :key="a.action">
        <button :class="a.primary ? 'btn-primary' : 'btn-danger'" @click="dialog = a">{{ a.label }}</button>
      </template>
    </PageHeader>

    <div class="grid gap-6 lg:grid-cols-3">
      <section class="panel p-5 lg:col-span-2">
        <div class="flex items-center gap-3"><StatusBadge :status="org.status" /><span class="text-xs text-neutral-500">/{{ org.slug }}</span></div>
        <dl class="mt-5 grid gap-4 text-sm sm:grid-cols-2">
          <div><dt class="text-xs text-neutral-500">Owner</dt><dd class="mt-0.5">{{ org.owner.name || '–' }}<br /><span class="text-neutral-600">{{ org.owner.email }}</span></dd></div>
          <div><dt class="text-xs text-neutral-500">Contact phone</dt><dd class="mt-0.5">{{ org.contact_phone || '–' }}</dd></div>
          <div><dt class="text-xs text-neutral-500">Website</dt><dd class="mt-0.5 break-all">
            <a v-if="org.website" :href="org.website" target="_blank" rel="noopener noreferrer" class="link">{{ org.website }}</a><span v-else>–</span></dd></div>
          <div><dt class="text-xs text-neutral-500">Submitted</dt><dd class="mt-0.5">{{ formatDate(org.submitted_at) }}</dd></div>
          <div class="sm:col-span-2"><dt class="text-xs text-neutral-500">About</dt><dd class="mt-0.5 whitespace-pre-line">{{ org.description || '–' }}</dd></div>
        </dl>
        <div v-if="org.review_note" class="mt-5 rounded-md border border-neutral-200 bg-neutral-50 p-3 text-sm">
          <p class="text-xs text-neutral-500">Last review by {{ org.reviewed_by || 'unknown' }} · {{ formatDate(org.reviewed_at) }}</p>
          <p class="mt-1 whitespace-pre-line">{{ org.review_note }}</p>
        </div>
      </section>

      <section class="space-y-3">
        <StatTile label="Active members" :value="org.member_count" />
        <StatTile label="Exams" :value="org.exam_count" />
      </section>
    </div>

    <section class="panel mt-6">
      <h2 class="border-b border-neutral-200 px-4 py-3 text-sm font-semibold">History</h2>
      <p v-if="!org.history.length" class="px-4 py-6 text-sm text-neutral-500">No recorded actions.</p>
      <ul v-else class="divide-y divide-neutral-100">
        <li v-for="h in org.history" :key="h.id" class="flex flex-col gap-0.5 px-4 py-3 text-sm sm:flex-row sm:justify-between">
          <span><strong class="font-medium">{{ humanize(h.action) }}</strong><span class="text-neutral-500"> by {{ h.actor || 'system' }}</span>
            <span v-if="h.metadata.note" class="block text-neutral-600">“{{ h.metadata.note }}”</span></span>
          <span class="shrink-0 text-xs text-neutral-500">{{ formatDate(h.created_at) }}</span>
        </li>
      </ul>
    </section>
  </StateBlock>

  <ConfirmDialog :open="!!dialog" :title="dialog?.label" :message="dialog?.message" :confirm-label="dialog?.label"
    :danger="!dialog?.primary" :reason-label="dialog?.reason" :reason-required="dialog?.reasonRequired" :action="run" @close="dialog = null" />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import StatTile from '@/components/StatTile.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { platform } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { formatDate, humanize } from '@/format'

const route = useRoute()
const org = ref(null)
const loading = ref(true)
const error = ref(null)
const dialog = ref(null)

const ACTIONS = {
  pending: [
    { action: 'approve', label: 'Approve', primary: true, message: 'The organisation can invite members and run exams immediately.', reason: 'Note to the owner' },
    { action: 'reject', label: 'Reject', message: 'The owner sees your reason and can update and resubmit the application.', reason: 'Reason', reasonRequired: true },
  ],
  approved: [
    { action: 'suspend', label: 'Suspend', message: 'Members lose access at once and running exams end; saved answers are graded.', reason: 'Reason', reasonRequired: true },
  ],
  suspended: [
    { action: 'reactivate', label: 'Reactivate', primary: true, message: 'Members regain access to the organisation.', reason: 'Note' },
  ],
  rejected: [],
}
const actions = computed(() => ACTIONS[org.value?.status] || [])

async function load() {
  loading.value = true
  error.value = null
  try {
    org.value = await platform.organisation(route.params.id)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

async function run(note) {
  try {
    org.value = await platform.act(org.value.id, dialog.value.action, note)
    toast.success(`Organisation ${org.value.status}`)
  } catch (e) {
    toast.error(e)
    if (e.code === 'invalid_transition') await load()
    throw e
  }
}

onMounted(load)
</script>
