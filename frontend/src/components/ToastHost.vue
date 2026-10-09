<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4 sm:items-end sm:pr-6" aria-live="polite">
    <div
      v-for="t in toasts"
      :key="t.id"
      class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-md border px-4 py-3 text-sm shadow-sm"
      :class="t.kind === 'error' ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 bg-white text-neutral-900'"
      role="status"
    >
      <component :is="t.kind === 'error' ? AlertCircle : CheckCircle2" class="mt-0.5 h-4 w-4 shrink-0" />
      <p class="flex-1">{{ t.message }}</p>
      <button class="opacity-60 hover:opacity-100" aria-label="Dismiss" @click="dismiss(t.id)"><X class="h-4 w-4" /></button>
    </div>
  </div>
</template>

<script setup>
import { AlertCircle, CheckCircle2, X } from 'lucide-vue-next'
import { toasts, dismiss } from '@/stores/toast'
</script>
