<template>
  <div class="min-h-screen bg-neutral-50">
    <header class="flex h-14 items-center justify-between border-b border-neutral-200 bg-white px-4 sm:px-6">
      <span class="text-sm font-semibold tracking-tight">ParallaxLane</span>
      <div class="flex items-center gap-3">
        <span class="hidden text-xs text-neutral-500 sm:inline">{{ session.state.me?.email }}</span>
        <button class="btn-ghost" @click="signOut"><LogOut class="h-4 w-4" />Sign out</button>
      </div>
    </header>
    <main class="mx-auto max-w-2xl px-4 py-8 sm:px-6"><slot /></main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { LogOut } from 'lucide-vue-next'
import { session } from '@/stores/session'

const router = useRouter()
async function signOut() {
  await session.logout()
  router.replace({ name: 'login' })
}
</script>
