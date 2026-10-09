<template>
  <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <RouterLink v-if="back" :to="back" class="mb-2 inline-flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-900">
        <ArrowLeft class="h-3.5 w-3.5" />{{ backLabel || 'Back' }}
      </RouterLink>
      <h1 class="text-xl font-semibold tracking-tight">{{ title }}</h1>
      <p v-if="description" class="mt-1 text-sm text-neutral-500">{{ description }}</p>
    </div>
    <div class="flex flex-wrap gap-2"><slot /></div>
  </div>
</template>

<script setup>
import { ArrowLeft } from 'lucide-vue-next'
defineProps({ title: String, description: String, back: [Object, String], backLabel: String })
</script>
