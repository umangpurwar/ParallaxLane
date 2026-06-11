<template>
  <span
    class="inline-flex items-center px-2.5 py-1 text-[8px] uppercase tracking-widest font-bold border-2"
    :class="badgeClass"
  >
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  plan: {
    type: String,
    default: 'free',
  },
})

const label = computed(() => (props.plan || 'free').toUpperCase())

const badgeClass = computed(() => {
  const p = (props.plan || 'free').toLowerCase()
  if (p === 'enterprise') {
    return 'border-brutal-ink bg-brutal-ink text-white'
  }
  if (p === 'pro') {
    return 'border-brutal-red bg-brutal-red text-white'
  }
  return 'border-brutal-border bg-white text-gray-600'
})
</script>
