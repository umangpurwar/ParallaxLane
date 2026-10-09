<template>
  <PageHeader title="Overview" :description="data ? `Signed in as ${data.your_role}` : ''" />
  <StateBlock :loading="loading" :error="error" @retry="load">
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatTile label="Active members" :value="data.members.total" :hint="roleHint" :to="{ name: 'org-members', params: { slug } }" />
      <StatTile label="Exams" :value="data.exams.total" :hint="`${data.exams.published} published, ${data.exams.active} open now`" :to="{ name: 'org-exams', params: { slug } }" />
      <StatTile label="Exams in progress" :value="data.active_attempts" hint="Candidates taking an exam right now" />
      <StatTile label="Pending invitations" :value="data.pending_invites" :to="{ name: 'org-invites', params: { slug } }" />
    </div>

    <div v-if="data.pending_devices" class="panel mt-6 flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-sm"><strong>{{ data.pending_devices }}</strong> phone{{ data.pending_devices === 1 ? '' : 's' }} waiting for approval. Candidates cannot take exams on a phone you have not approved.</p>
      <RouterLink :to="{ name: 'org-devices', params: { slug } }" class="btn-primary">Review phones</RouterLink>
    </div>

    <div class="mt-6 grid gap-6 lg:grid-cols-2">
      <section class="panel p-5">
        <h2 class="text-sm font-semibold">Organisation</h2>
        <dl class="mt-4 space-y-3 text-sm">
          <div class="flex justify-between gap-4"><dt class="text-neutral-500">Status</dt><dd><StatusBadge :status="data.organisation.status" /></dd></div>
          <div class="flex justify-between gap-4"><dt class="text-neutral-500">Plan</dt><dd class="capitalize">{{ data.plan }}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-neutral-500">Approved</dt><dd>{{ formatDate(data.organisation.reviewed_at) }}</dd></div>
        </dl>
      </section>
      <section class="panel p-5">
        <h2 class="text-sm font-semibold">Plan limits</h2>
        <dl class="mt-4 space-y-3 text-sm">
          <div v-for="(value, key) in data.limits" :key="key" class="flex justify-between gap-4"><dt class="text-neutral-500">{{ humanize(key) }}</dt><dd class="tabular-nums">{{ value }}</dd></div>
        </dl>
      </section>
    </div>
  </StateBlock>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatTile from '@/components/StatTile.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { org } from '@/api/endpoints'
import { formatDate, humanize } from '@/format'

const route = useRoute()
const slug = computed(() => route.params.slug)
const data = ref(null)
const loading = ref(true)
const error = ref(null)
const roleHint = computed(() => Object.entries(data.value?.members.by_role || {}).map(([r, n]) => `${n} ${r}`).join(', '))

async function load() {
  loading.value = true
  error.value = null
  try {
    data.value = await org.overview(slug.value)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}
watch(slug, load, { immediate: true })
</script>
