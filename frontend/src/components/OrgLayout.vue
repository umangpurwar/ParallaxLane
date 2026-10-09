<template>
  <AppShell :title="orgName" :subtitle="orgName" :items="items">
    <template #footer>
      <RouterLink v-if="session.adminOrgs().length > 1" :to="{ name: 'org-picker' }" class="btn-ghost mt-1 w-full justify-start">
        <ArrowLeftRight class="h-4 w-4" />Switch organisation
      </RouterLink>
    </template>
  </AppShell>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftRight, ClipboardList, LayoutDashboard, Mail, ScrollText, Settings, Smartphone, Users } from 'lucide-vue-next'
import AppShell from './AppShell.vue'
import { session } from '@/stores/session'

const route = useRoute()
const slug = computed(() => route.params.slug)
const orgName = computed(() => session.adminOrgs().find((m) => m.slug === slug.value)?.name || 'Organisation')
const items = computed(() => [
  { label: 'Overview', to: { name: 'org-overview', params: { slug: slug.value } }, icon: LayoutDashboard, exact: true },
  { label: 'Exams', to: { name: 'org-exams', params: { slug: slug.value } }, icon: ClipboardList },
  { label: 'Members', to: { name: 'org-members', params: { slug: slug.value } }, icon: Users },
  { label: 'Invitations', to: { name: 'org-invites', params: { slug: slug.value } }, icon: Mail },
  { label: 'Phone approvals', to: { name: 'org-devices', params: { slug: slug.value } }, icon: Smartphone },
  { label: 'Settings', to: { name: 'org-settings', params: { slug: slug.value } }, icon: Settings },
  { label: 'Audit log', to: { name: 'org-audit', params: { slug: slug.value } }, icon: ScrollText },
])
</script>
