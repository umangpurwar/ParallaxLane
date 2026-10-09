<template>
  <SimpleShell>
    <div class="panel p-6">
      <h1 class="text-lg font-semibold">Use the ParallaxLane app</h1>
      <p class="mt-2 text-sm text-neutral-600">
        Your account is a member of
        <strong>{{ names }}</strong>. Members take exams in the ParallaxLane Android app. This dashboard is for organisation administrators.
      </p>
      <RouterLink :to="{ name: 'apply' }" class="link mt-4 inline-block text-sm">Register a new organisation instead</RouterLink>
    </div>
  </SimpleShell>
</template>

<script setup>
import { computed } from 'vue'
import SimpleShell from '@/components/SimpleShell.vue'
import { session } from '@/stores/session'
const names = computed(() => (session.state.me?.memberships || []).map((m) => m.name).join(', '))
</script>
