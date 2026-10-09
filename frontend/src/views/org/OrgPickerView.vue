<template>
  <SimpleShell>
    <PageHeader title="Choose an organisation" />
    <div class="panel divide-y divide-neutral-100">
      <RouterLink v-for="m in session.adminOrgs()" :key="m.slug" :to="{ name: 'org-overview', params: { slug: m.slug } }"
        class="flex items-center justify-between px-5 py-4 hover:bg-neutral-50">
        <div>
          <p class="font-medium">{{ m.name }}</p>
          <p class="text-xs text-neutral-500">{{ m.role }}</p>
        </div>
        <ChevronRight class="h-4 w-4 text-neutral-400" />
      </RouterLink>
    </div>
  </SimpleShell>
</template>

<script setup>
import { ChevronRight } from 'lucide-vue-next'
import SimpleShell from '@/components/SimpleShell.vue'
import PageHeader from '@/components/PageHeader.vue'
import { session } from '@/stores/session'
</script>
