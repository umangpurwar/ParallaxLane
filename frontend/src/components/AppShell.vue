<template>
  <div class="min-h-screen bg-neutral-50">
    <header class="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-neutral-200 bg-white px-4 lg:hidden">
      <button class="btn-ghost h-9 w-9 px-0" aria-label="Open menu" @click="open = true"><Menu class="h-5 w-5" /></button>
      <span class="text-sm font-semibold">{{ title }}</span>
    </header>

    <div v-if="open" class="fixed inset-0 z-40 bg-neutral-900/30 lg:hidden" @click="open = false"></div>
    <aside
      class="fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-neutral-200 bg-white transition-transform lg:translate-x-0"
      :class="open ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="flex h-14 items-center justify-between border-b border-neutral-200 px-4">
        <div>
          <p class="text-sm font-semibold tracking-tight">ParallaxLane</p>
          <p class="truncate text-xs text-neutral-500" :title="subtitle">{{ subtitle }}</p>
        </div>
        <button class="btn-ghost h-8 w-8 px-0 lg:hidden" aria-label="Close menu" @click="open = false"><X class="h-4 w-4" /></button>
      </div>
      <nav class="flex-1 space-y-0.5 overflow-y-auto p-2">
        <RouterLink
          v-for="item in items"
          :key="item.label"
          :to="item.to"
          class="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
          :active-class="item.exact ? '' : '!bg-neutral-900 !text-white'"
          exact-active-class="!bg-neutral-900 !text-white"
          @click="open = false"
        >
          <component :is="item.icon" class="h-4 w-4" />
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="border-t border-neutral-200 p-3">
        <p class="truncate px-1 text-xs text-neutral-500">{{ session.state.me?.email }}</p>
        <slot name="footer" />
        <button class="btn-ghost mt-1 w-full justify-start" @click="signOut"><LogOut class="h-4 w-4" />Sign out</button>
      </div>
    </aside>

    <main class="lg:pl-60">
      <div class="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
        <RouterView />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { LogOut, Menu, X } from 'lucide-vue-next'
import { session } from '@/stores/session'

defineProps({ title: String, subtitle: String, items: Array })
const open = ref(false)
const router = useRouter()

async function signOut() {
  await session.logout()
  router.replace({ name: 'login' })
}
</script>
