<template>
  <div v-if="data && data.num_pages > 1" class="flex items-center justify-between border-t border-neutral-200 px-4 py-3 text-sm">
    <span class="text-neutral-500">Page {{ data.page }} of {{ data.num_pages }} · {{ data.count }} total</span>
    <div class="flex gap-2">
      <button class="btn-secondary h-8" :disabled="data.page <= 1" @click="$emit('page', data.page - 1)">Previous</button>
      <button class="btn-secondary h-8" :disabled="data.page >= data.num_pages" @click="$emit('page', data.page + 1)">Next</button>
    </div>
  </div>
</template>

<script setup>
defineProps({ data: Object })
defineEmits(['page'])
</script>
