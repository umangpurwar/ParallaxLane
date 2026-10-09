<template>
  <AppShell title="Super admin" subtitle="Platform administration" :items="items" />
</template>

<script setup>
import { Building2, LayoutDashboard, ScrollText } from 'lucide-vue-next'
import AppShell from './AppShell.vue'

const items = [
  { label: 'Overview', to: { name: 'platform-overview' }, icon: LayoutDashboard, exact: true },
  { label: 'Organisations', to: { name: 'platform-orgs' }, icon: Building2 },
  { label: 'Audit log', to: { name: 'platform-audit' }, icon: ScrollText },
]
</script>
