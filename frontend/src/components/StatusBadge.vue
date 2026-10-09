<template>
  <span class="inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium" :class="style.cls">
    <span class="h-1.5 w-1.5 rounded-full" :class="style.dot"></span>{{ label || status }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String, label: String })
// Monochrome: weight and fill carry the meaning instead of colour.
const strong = ['approved', 'active', 'accepted', 'completed', 'open', 'published']
const muted = ['rejected', 'revoked', 'expired', 'declined', 'inactive', 'closed', 'draft', 'disabled']
const style = computed(() => {
  if (props.status === 'suspended' || props.status === 'terminated') return { cls: 'border-neutral-900 bg-neutral-900 text-white', dot: 'bg-white' }
  if (strong.includes(props.status)) return { cls: 'border-neutral-300 bg-white text-neutral-900', dot: 'bg-neutral-900' }
  if (muted.includes(props.status)) return { cls: 'border-neutral-200 bg-neutral-100 text-neutral-500', dot: 'bg-neutral-400' }
  return { cls: 'border-neutral-400 border-dashed bg-white text-neutral-700', dot: 'bg-neutral-500' }
})
</script>
