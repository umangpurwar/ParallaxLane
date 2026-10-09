<template>
  <component :is="to ? 'RouterLink' : 'div'" :to="to" class="panel block p-4" :class="to ? 'hover:border-neutral-400' : ''">
    <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">{{ label }}</p>
    <p class="mt-2 text-2xl font-semibold tabular-nums">{{ value ?? '–' }}</p>
    <p v-if="hint" class="mt-1 text-xs text-neutral-500">{{ hint }}</p>
  </component>
</template>

<script setup>
defineProps({ label: String, value: [Number, String], hint: String, to: [Object, String] })
</script>
