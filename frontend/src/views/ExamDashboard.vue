<template>
  <div class="relative w-full h-screen overflow-hidden bg-brutal-paper font-sans">
    
    <transition name="reveal" appear>
      <div class="relative z-10 w-full h-full flex flex-col overflow-hidden">
        
        <div class="absolute inset-0 pointer-events-none z-0">
            <div class="grid-line-v left-[30%]"></div>
            <div class="grid-line-v left-[65%]"></div>
            <div class="grid-line-h top-[12%]"></div>
        </div>

        <header class="absolute top-0 left-0 w-full h-[12%] flex z-20">
            <div class="w-[30%] h-full flex items-center px-8 font-bold tracking-super-wide text-[13px] text-black">
                PARALLAXLANE
            </div>
            <div class="w-[35%] h-full flex items-center px-8 text-[9px] uppercase tracking-widest font-semibold text-gray-700">
                STUDENT DASHBOARD
            </div>
            <div class="w-[35%] h-full flex items-center px-8 justify-end">
                
                <div v-if="currentOrg" class="flex items-center gap-2 mr-6 border-r border-brutal-border/50 pr-6">
                    <span class="text-[9px] uppercase tracking-widest font-bold text-brutal-red">
                        {{ currentOrg }}
                    </span>
                    <select v-if="organisations.length > 1" 
                            @change="switchOrganisation" 
                            :disabled="isSwitching"
                            class="bg-transparent border border-brutal-border text-[9px] uppercase tracking-widest font-bold text-gray-700 py-1 px-2 focus:outline-none cursor-pointer hover:border-brutal-ink transition-colors"
                            :class="{'opacity-50 cursor-wait': isSwitching}">
                        <option value="" disabled selected>SWITCH</option>
                        <option v-for="org in organisations" :key="org.slug" :value="org.slug" :disabled="org.name === currentOrg">
                            {{ org.name }}
                        </option>
                    </select>
                </div>

                <div class="text-[9px] uppercase tracking-widest font-bold text-gray-500 mr-8">
                    TOTAL VIOLATIONS: 
                    <span :class="totalViolations > 0 ? 'text-brutal-red text-[11px]' : 'text-brutal-ink text-[11px]'">
                        {{ totalViolations }}
                    </span>
                </div>
                <button @click="logout" class="text-[9px] uppercase tracking-widest font-bold text-brutal-red hover:text-brutal-ink transition-colors pointer-events-auto">
                    LOG OUT
                </button>
            </div>
        </header>

        <main class="absolute top-[12%] bottom-0 left-0 w-full flex z-10 pointer-events-auto">
            
            <div class="w-[30%] h-full p-8 md:p-12 flex flex-col border-r border-transparent overflow-hidden">
                <p class="text-[9px] uppercase tracking-wide-ish font-semibold text-gray-600 mb-4 shrink-0">
                    Candidate Profile
                </p>
                <h1 class="text-[2.5rem] lg:text-[3rem] font-medium tracking-tighter leading-none text-brutal-ink mb-12 capitalize shrink-0">
                    Welcome,<br>{{ username }}
                </h1>

                <div class="flex-1 flex flex-col overflow-hidden border-t border-brutal-border/30 pt-8">
                    <p class="text-[9px] uppercase tracking-wide-ish font-semibold text-gray-600 mb-6 shrink-0">
                        Upcoming Evaluations
                    </p>
                    
                    <div class="flex-1 overflow-y-auto pr-4 pb-4 flex flex-col gap-6">
                        <div v-for="exam in upcomingExams" :key="exam.id" class="group cursor-pointer">
                            <p class="text-[10px] font-bold text-gray-500 mb-1 uppercase">{{ formatDate(exam.start_time) || 'DATE PENDING' }}</p>
                            <h4 class="text-lg font-medium tracking-tight text-brutal-ink group-hover:text-brutal-red transition-colors truncate">
                              {{ exam.title }}
                            </h4>
                            <div class="h-[1px] w-full bg-brutal-border mt-4 opacity-50"></div>
                        </div>
                        <div v-if="upcomingExams.length === 0" class="text-sm font-medium text-gray-400 italic mt-2">
                            No upcoming exams scheduled.
                        </div>
                    </div>
                </div>
            </div>

            <div class="w-[35%] h-full p-8 md:p-12 flex flex-col overflow-hidden">
                <p class="text-[9px] uppercase tracking-wide-ish font-bold text-brutal-red mb-6 flex items-center gap-2 shrink-0">
                    <span class="w-2 h-2 rounded-full bg-brutal-red animate-pulse"></span>
                    Action Required
                </p>
                
                <div class="flex-1 overflow-y-auto pr-4 pb-4" v-if="activeExam.length">
                    <div v-for="exam in activeExam" :key="exam.id" class="bg-brutal-ink text-brutal-paper p-8 shadow-2xl mb-6 shrink-0 border border-brutal-ink">
                        <h3 class="text-xl font-medium tracking-tight mb-2 truncate">{{ exam.title }}</h3>
                        <p class="text-xs text-gray-400 mb-6">Proctoring: Enabled • Duration: {{ exam.duration }} mins</p>

                        <button 
                            :disabled="!exam.is_active"
                            @click="startExam(exam.id)"
                            class="w-full bg-brutal-red hover:bg-white hover:text-brutal-ink text-white py-3 text-[10px] uppercase tracking-super-wide font-bold transition-all duration-300">
                            Begin Exam Now
                        </button>
                    </div>
                </div>
                
                <div class="flex-1" v-else>
                    <div class="bg-white border border-brutal-border text-brutal-ink p-8">
                        <h3 class="text-xl font-medium tracking-tight mb-2">You're all caught up!</h3>
                        <p class="text-xs text-gray-500">Check back later for new assessments.</p>
                    </div>
                </div>
            </div>

            <div class="w-[35%] h-full p-8 md:p-12 flex flex-col relative overflow-hidden">
                <p class="text-[9px] uppercase tracking-wide-ish font-semibold text-gray-600 mb-8 shrink-0">
                    Verified Results
                </p>

                <div class="flex-1 overflow-y-auto pr-4 pb-4 flex flex-col gap-4">
                    <div v-for="result in pastResults" :key="result.id" 
                         @click="openResultModal(result)"
                         class="flex justify-between items-end pb-4 border-b border-brutal-border border-opacity-50 cursor-pointer group hover:bg-black/5 p-2 transition-colors shrink-0">
                        <div class="overflow-hidden pr-4 flex-1">
                            <h4 class="text-md font-medium tracking-tight text-brutal-ink truncate group-hover:text-brutal-red transition-colors">{{ result.exam_title }}</h4>
                            <p class="text-[9px] uppercase tracking-widest text-gray-500 mt-1">
                                Status: {{ result.status }} 
                                <span class="mx-1">•</span> 
                                Violations: <span :class="result.violations > 0 ? 'text-brutal-red font-bold' : 'text-brutal-ink'">{{ result.violations || 0 }}</span>
                            </p>
                        </div>
                        <span class="text-2xl font-medium tracking-tighter shrink-0">
                         {{ result.score }}/{{ result.total_questions }}
                        </span>
                    </div>

                    <div v-if="pastResults.length === 0" class="text-sm font-medium text-gray-400 italic">
                        No verified results available yet.
                    </div>
                </div>

                <div class="mt-auto pt-4 shrink-0 bg-brutal-paper">
                    <p class="text-[9px] uppercase tracking-wide-ish leading-[1.6] font-semibold text-gray-500">
                        All evaluations secured and verified<br>by ParallaxLane Protocol.
                    </p>
                </div>
            </div>

        </main>
        
        <div v-if="showResultModal && selectedResult" class="fixed inset-0 z-[120] bg-brutal-dark/90 backdrop-blur-md flex items-center justify-center p-8 pointer-events-auto">
          <div class="bg-brutal-paper border-4 border-brutal-ink p-8 max-w-lg w-full shadow-[8px_8px_0px_0px_rgba(239,63,35,1)] flex flex-col">
            
            <div class="flex justify-between items-start mb-6 border-b-2 border-brutal-ink pb-4">
              <div class="overflow-hidden pr-4">
                <h3 class="text-2xl font-black tracking-tighter text-brutal-ink uppercase truncate">{{ selectedResult.exam_title }}</h3>
                <p class="text-sm font-bold text-gray-600 mt-1">
                  Status: <span :class="selectedResult.status === 'Terminated' ? 'text-brutal-red' : 'text-emerald-600'">{{ selectedResult.status }}</span>
                </p>
              </div>
            </div>

            <div class="flex justify-between items-end mb-8 bg-white border-2 border-brutal-ink p-4">
              <span class="text-[10px] uppercase tracking-widest font-bold text-gray-500">Final Score</span>
              <span class="text-5xl font-black tracking-tighter" :class="selectedResult.status === 'Terminated' ? 'text-brutal-red' : 'text-brutal-ink'">
                {{ calculatePercentage(selectedResult.score, selectedResult.total_questions) }}%
              </span>
            </div>

            <h4 class="text-[10px] uppercase tracking-super-wide font-black text-brutal-red mb-4">
              Violation History Log ({{ selectedResult.violations }})
            </h4>

            <div class="flex-1 overflow-y-auto max-h-48 border-2 border-brutal-border bg-white p-4 mb-6">
              <div v-if="selectedResult.violation_details && selectedResult.violation_details.length > 0" class="flex flex-col gap-3">
                <div v-for="(v, idx) in selectedResult.violation_details" :key="idx" class="flex justify-between items-center border-b border-gray-200 pb-2 last:border-0 last:pb-0">
                  <span class="text-xs font-bold text-brutal-ink">{{ v.type }}</span>
                  <span class="text-[10px] font-bold text-gray-500">{{ v.time }}</span>
                </div>
              </div>
              <div v-else class="text-sm font-bold text-gray-400 italic text-center py-4">
                No violations recorded. Clean run!
              </div>
            </div>

            <button @click="closeResultModal" class="w-full bg-brutal-ink text-white py-4 text-[10px] uppercase tracking-super-wide font-black hover:bg-brutal-red transition-colors">
              Close Report
            </button>
          </div>
        </div>

        <div class="absolute bottom-6 right-8 pointer-events-none text-[9px] uppercase tracking-super-wide font-bold text-gray-500 z-30">
            &copy; UMNG
        </div>
        
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import api, { setAuthData } from "../services/api"

const router = useRouter()
const username = ref("Student")

const allExams = ref([])
const pastResults = ref([])

// NEW: Multi-tenant State
const organisations = ref([])
const currentOrg = ref("")
const isSwitching = ref(false)

// Modal States
const showResultModal = ref(false)
const selectedResult = ref(null)

const calculatePercentage = (score, total) => {
  if (!total || total === 0) return 0;
  return Math.round((score / total) * 100);
}

const openResultModal = (result) => {
  selectedResult.value = result
  showResultModal.value = true
}

const closeResultModal = () => {
  showResultModal.value = false
  selectedResult.value = null
}

const totalViolations = computed(() => {
  return pastResults.value.reduce((sum, result) => sum + (result.violations || 0), 0)
})

// idle timer
let idleTimer = null
const IDLE_TIMEOUT_MS = 5 * 60 * 1000 

const resetIdleTimer = () => {
  if (idleTimer) clearTimeout(idleTimer)
  idleTimer = setTimeout(() => {
    localStorage.clear()
    router.push('/login')
  }, IDLE_TIMEOUT_MS)
}

const setupActivityListeners = () => {
  window.addEventListener('mousemove', resetIdleTimer)
  window.addEventListener('keydown', resetIdleTimer)
  window.addEventListener('click', resetIdleTimer)
  resetIdleTimer() 
}

const cleanupActivityListeners = () => {
  window.removeEventListener('mousemove', resetIdleTimer)
  window.removeEventListener('keydown', resetIdleTimer)
  window.removeEventListener('click', resetIdleTimer)
  if (idleTimer) clearTimeout(idleTimer)
}

const fetchDashboardData = async () => {
  try {
    const examRes = await api.get('exams/')
    allExams.value = examRes.data || []

    try {
      const resultsRes = await api.get('exams/my-results/')
      pastResults.value = resultsRes.data || []
    } catch (err) {
      console.warn("My Results endpoint missing/failed. Displaying empty state.")
    }
  } catch (error) {
    console.error("Failed to load dashboard data", error)
  }
}

// NEW: Fetch user organisations
const fetchOrganisations = async () => {
  try {
    const res = await api.get('organisations/mine/')
    organisations.value = res.data || []
  } catch (error) {
    console.error("Failed to load organisations", error)
  }
}

// NEW: Switch Organisation
const switchOrganisation = async (event) => {
  const slug = event.target.value
  if (!slug) return
  
  isSwitching.value = true
  
  try {
    const res = await api.post(`organisations/${slug}/switch/`)
    const data = res.data

    setAuthData({
      org_slug: data.org_slug,
      org_name: data.org_name,
      org_role: data.org_role,
      org_plan: data.org_plan
    })

    currentOrg.value = data.org_name
    event.target.value = "" // Reset dropdown
    
    await fetchDashboardData()
  } catch (error) {
    console.error("Failed to switch organisation", error)
  } finally {
    isSwitching.value = false
  }
}

let dashboardInterval = null 

onMounted(() => {
  const storedName = localStorage.getItem("username")
  if (storedName) {
    username.value = storedName
  }

  // Load current organisation name
  const storedOrgName = localStorage.getItem("org_name")
  if (storedOrgName) {
    currentOrg.value = storedOrgName
  }

  fetchDashboardData()
  dashboardInterval = setInterval(fetchDashboardData, 5000)
  setupActivityListeners()
  
  fetchOrganisations()
})

onUnmounted(() => {
  cleanupActivityListeners()

  if (dashboardInterval) {
    clearInterval(dashboardInterval)
  }
})

const activeExam = computed(() => {
  return allExams.value.filter(e => e.is_active) || []
})

const upcomingExams = computed(() => {
  return allExams.value.filter(e => !e.is_active).slice(0, 4) || []
})

const startExam = (examId) => {
  // 1. Remove specific safe keys
  localStorage.removeItem("attempt_id");
  localStorage.removeItem("active_exam_id");
  // 2. Safely iterate and remove any keys starting with 'exam_state_'
  Object.keys(localStorage).forEach(key => {
    if (key.startsWith("exam_state_")) {
      localStorage.removeItem(key);
    }
  });
  // 3. Initialize new exam state and navigate
  localStorage.setItem("active_exam_id", examId);
  router.push({
    name: 'Exam',
    params: { id: examId }
  });
}

const formatDate = (dateString) => {
  if (!dateString) return null;
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const logout = () => {
  localStorage.clear()
  router.push("/login")
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');
.font-sans { font-family: 'Inter', sans-serif; }

/* custom scroll bar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #b5b0a6; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #ef3f23; }

.grid-line-v { position: absolute; top: 0; bottom: 0; width: 1px; background-image: linear-gradient(to bottom, #b5b0a6 50%, transparent 50%); background-size: 1px 6px; }
.grid-line-h { position: absolute; left: 0; right: 0; height: 1px; background-image: linear-gradient(to right, #b5b0a6 50%, transparent 50%); background-size: 6px 1px; }

.reveal-enter-active { transition: opacity 0.8s ease, transform 0.8s cubic-bezier(0.2, 0.8, 0.2, 1); }
.reveal-enter-from { opacity: 0; transform: scale(0.98); }
</style>