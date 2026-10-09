<template>
  <div class="flex min-h-screen items-center justify-center bg-neutral-50 px-4 py-10">
    <div class="w-full max-w-sm">
      <p class="mb-6 text-center text-sm font-semibold tracking-tight">ParallaxLane</p>
      <div class="panel p-6">
        <h1 class="text-lg font-semibold">{{ title }}</h1>
        <p v-if="description" class="mt-1 text-sm text-neutral-500">{{ description }}</p>
        <div class="mt-6"><slot /></div>
      </div>
      <div class="mt-4 text-center text-sm text-neutral-500"><slot name="below" /></div>
    </div>
  </div>
</template>

<script setup>
defineProps({ title: String, description: String })
</script>
