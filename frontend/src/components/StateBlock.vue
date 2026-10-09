<template>
  <div v-if="loading" class="flex items-center justify-center gap-2 py-16 text-sm text-neutral-500">
    <Loader2 class="h-4 w-4 animate-spin" />Loading…
  </div>
  <div v-else-if="error" class="flex flex-col items-center gap-3 py-16 text-center">
    <p class="text-sm text-neutral-700">{{ error.message }}</p>
    <button class="btn-secondary" @click="$emit('retry')">Try again</button>
  </div>
  <div v-else-if="empty" class="flex flex-col items-center gap-2 py-16 text-center">
    <component :is="icon || Inbox" class="h-6 w-6 text-neutral-400" />
    <p class="text-sm font-medium">{{ emptyTitle || 'Nothing here yet' }}</p>
    <p v-if="emptyText" class="max-w-sm text-sm text-neutral-500">{{ emptyText }}</p>
    <slot name="empty-action" />
  </div>
  <slot v-else />
</template>

<script setup>
import { Inbox, Loader2 } from 'lucide-vue-next'
defineProps({ loading: Boolean, error: Object, empty: Boolean, emptyTitle: String, emptyText: String, icon: Object })
defineEmits(['retry'])
</script>
