<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-end justify-center bg-neutral-900/40 p-4 sm:items-center" @mousedown.self="$emit('close')">
      <div class="w-full max-w-md rounded-lg border border-neutral-200 bg-white shadow-lg" role="dialog" aria-modal="true" :aria-label="title">
        <div class="flex items-center justify-between border-b border-neutral-200 px-5 py-3">
          <h2 class="text-sm font-semibold">{{ title }}</h2>
          <button class="btn-ghost h-8 w-8 px-0" aria-label="Close" @click="$emit('close')"><X class="h-4 w-4" /></button>
        </div>
        <div class="px-5 py-4"><slot /></div>
        <div v-if="$slots.footer" class="flex justify-end gap-2 border-t border-neutral-200 px-5 py-3"><slot name="footer" /></div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onBeforeUnmount, watch } from 'vue'
import { X } from 'lucide-vue-next'
const props = defineProps({ open: Boolean, title: String })
const emit = defineEmits(['close'])
const onKey = (e) => { if (e.key === 'Escape') emit('close') }
watch(() => props.open, (value) => (value ? window.addEventListener('keydown', onKey) : window.removeEventListener('keydown', onKey)))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>
