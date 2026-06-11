<template>
  <div class="h-full flex flex-col">
    <div class="flex justify-between items-end mb-6">
      <div>
        <h2 class="text-2xl font-medium tracking-tight text-brutal-ink">Live Invigilation</h2>
        <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500 mt-1 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-brutal-red animate-pulse"></span>
          System Monitoring Active
        </p>
      </div>

      <div class="flex gap-2 text-[10px] uppercase tracking-widest font-semibold">
        <button
          @click="activeFilter = 'all'"
          :class="activeFilter === 'all' ? 'bg-brutal-ink text-white' : 'bg-white text-brutal-ink hover:bg-gray-50'"
          class="border border-brutal-border px-3 py-1 transition-colors"
        >
          All ({{ totalCandidates }})
        </button>
        <button
          @click="activeFilter = 'risk'"
          :class="activeFilter === 'risk' ? 'bg-brutal-red text-white' : 'bg-white text-brutal-red hover:bg-red-50'"
          class="border border-brutal-border px-3 py-1 transition-colors"
        >
          High Risk ({{ highRiskCount }})
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
      <div
        v-for="user in displayedUsers"
        :key="user.id"
        class="bg-white border border-brutal-border p-5 flex flex-col gap-4 transition-all hover:border-brutal-ink cursor-pointer overflow-hidden"
        :class="{ 'border-l-4 border-l-brutal-red': user.isHighRisk }"
        @click="$emit('open-modal', user)"
      >
        <div class="flex items-start justify-between gap-3 min-w-0">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <div class="w-10 h-10 shrink-0 bg-brutal-ink text-brutal-paper flex items-center justify-center font-bold text-sm uppercase">
              {{ user.initials }}
            </div>
            <div class="min-w-0 flex-1">
              <h3 class="font-medium tracking-tight text-brutal-ink truncate" :title="user.name">
                {{ user.name }}
              </h3>
              <p
                class="text-[9px] uppercase tracking-widest font-semibold mt-1"
                :class="statusClass(user.status)"
              >
                {{ user.status }}
              </p>
            </div>
          </div>

          <div
            class="shrink-0 flex flex-col items-end gap-1 px-3 py-2 border-2 min-w-[88px]"
            :class="user.isHighRisk ? 'border-brutal-red bg-red-50' : 'border-brutal-border bg-gray-50'"
          >
            <span class="text-[8px] uppercase tracking-widest font-bold text-gray-500 whitespace-nowrap">
              Risk Score
            </span>
            <span
              class="text-xl font-black leading-none"
              :class="user.isHighRisk ? 'text-brutal-red' : 'text-brutal-ink'"
            >
              {{ user.riskScore }}
            </span>
            <span
              class="text-[8px] uppercase tracking-widest font-bold whitespace-nowrap"
              :class="user.isHighRisk ? 'text-brutal-red' : 'text-gray-500'"
            >
              {{ user.riskLabel }}
            </span>
          </div>
        </div>

        <div class="h-px w-full bg-brutal-border/50"></div>

        <div class="grid grid-cols-3 gap-3 text-[10px] uppercase tracking-widest font-bold">
          <div class="flex flex-col gap-1">
            <span class="text-gray-500">Camera</span>
            <span :class="user.health.camera ? 'text-brutal-ink' : 'text-brutal-red'">
              {{ user.health.camera ? 'ON' : 'OFF' }}
            </span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-gray-500">Tab Focus</span>
            <span :class="user.health.tab ? 'text-brutal-ink' : 'text-brutal-red'">
              {{ user.health.tab ? 'ACTIVE' : 'AWAY' }}
            </span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-gray-500">Fullscreen</span>
            <span :class="user.health.fullscreen ? 'text-brutal-ink' : 'text-brutal-red'">
              {{ user.health.fullscreen ? 'ON' : 'EXIT' }}
            </span>
          </div>
        </div>
      </div>

      <div
        v-if="displayedUsers.length === 0"
        class="col-span-full py-12 text-center text-sm font-medium text-gray-500 border border-dashed border-brutal-border"
      >
        No candidates found matching this filter.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import api from '@/services/api'

defineEmits(['open-modal'])

const liveUsers = ref([])
const activeFilter = ref('all')
let pollingInterval = null
let isFetching = false

const RISK_HIGH_THRESHOLD = 10

const resolveDisplayName = (item) => {
  const firstLast = [item.first_name, item.last_name].filter(Boolean).join(' ').trim()
  if (firstLast) return firstLast
  if (item.display_name) return item.display_name
  if (item.username && !String(item.username).includes('@')) return item.username
  return item.username || 'Unknown'
}

const resolveInitials = (name) => {
  const parts = String(name).trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0].charAt(0)}${parts[parts.length - 1].charAt(0)}`.toUpperCase()
  }
  return (parts[0]?.charAt(0) || '?').toUpperCase()
}

const riskLabel = (score) => {
  if (score >= RISK_HIGH_THRESHOLD) return 'High Risk'
  if (score >= 5) return 'Medium Risk'
  return 'Low Risk'
}

const statusClass = (status) => {
  if (status === 'Active') return 'text-green-600'
  if (status === 'Terminated') return 'text-brutal-red'
  return 'text-gray-400'
}

const mapStatus = (status) => {
  if (status === 'active') return 'Active'
  if (status === 'terminated') return 'Terminated'
  return 'Inactive'
}

const fetchLiveMonitorData = async () => {
  if (isFetching) return
  isFetching = true

  const examId = localStorage.getItem('active_exam_id')
  try {
    if (!examId) return

    const response = await api.get(`admin/exam/${examId}/live/`)
    const data = response.data

    liveUsers.value = data.map((item) => {
      const name = resolveDisplayName(item)
      const riskScore = item.risk_score || 0
      const totalViolations = item.violations_count || 0
      const isHighRisk = totalViolations > 0 || riskScore >= RISK_HIGH_THRESHOLD

      return {
        id: item.attempt_id,
        username: item.username,
        email: item.username,
        name,
        initials: resolveInitials(name),
        status: mapStatus(item.status),
        riskScore,
        riskLabel: riskLabel(riskScore),
        isHighRisk,
        totalViolations,
        health: {
          camera: item.system_health?.camera ?? true,
          tab: item.system_health?.tab_focus ?? true,
          fullscreen: item.system_health?.fullscreen ?? true,
        },
      }
    })
  } catch (error) {
    console.error('Failed to fetch live monitoring data:', error)
  } finally {
    isFetching = false
  }
}

onMounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
  fetchLiveMonitorData()
  pollingInterval = setInterval(fetchLiveMonitorData, 5000)
})

onUnmounted(() => {
  if (pollingInterval) clearInterval(pollingInterval)
})

const totalCandidates = computed(() => liveUsers.value.length)

const highRiskUsersList = computed(() =>
  liveUsers.value.filter((u) => u.isHighRisk || u.status === 'Terminated')
)

const highRiskCount = computed(() => highRiskUsersList.value.length)

const displayedUsers = computed(() =>
  activeFilter.value === 'risk' ? highRiskUsersList.value : liveUsers.value
)
</script>
