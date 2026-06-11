<template>
  <div class="flex h-screen w-full bg-brutal-paper font-sans text-brutal-ink overflow-hidden">
    
    <aside class="w-64 bg-brutal-dark text-brutal-paper flex flex-col border-r border-brutal-border/30 z-20">
      <div class="h-20 flex items-center px-8 border-b border-brutal-border/30">
        <span class="font-bold tracking-super-wide text-[13px] text-white">PARALLAXLANE</span>
      </div>

      <nav class="flex-1 py-8 px-4 space-y-2">
        <button 
          v-for="tab in tabs" :key="tab.id"
          @click="activeTab = tab.id"
          class="w-full flex items-center px-4 py-3 text-[10px] uppercase tracking-widest font-semibold transition-all duration-200 border border-transparent"
          :class="activeTab === tab.id || (activeTab === 'create_exam' && tab.id === 'dashboard') ? 'bg-brutal-red text-white' : 'text-gray-400 hover:text-white hover:border-brutal-border/30'"
        >
          <span class="mr-3" v-html="tab.icon"></span>
          {{ tab.label }}
        </button>
      </nav>

      <div class="p-4 border-t border-brutal-border/30">
        <button @click="logout" class="w-full flex items-center px-4 py-3 text-[10px] uppercase tracking-widest font-semibold text-gray-400 hover:text-brutal-red transition-colors">
          <svg class="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
          Logout
        </button>
      </div>
    </aside>

    <div class="flex-1 flex flex-col relative overflow-hidden">
      
      <div class="absolute inset-0 pointer-events-none z-0">
          <div class="grid-line-v left-[33%]"></div>
          <div class="grid-line-v left-[66%]"></div>
      </div>

     <header class="h-20 flex items-center justify-between px-8 border-b border-brutal-border relative z-10 bg-brutal-paper">
        <div>
          <h1 class="text-2xl font-medium tracking-tight capitalize">Welcome, {{ adminName }}</h1>
          <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500 mt-1"> Invigilation Panel</p>
        </div>
        
        <div class="flex items-center gap-6">
          <div v-if="currentOrgName" class="flex items-center gap-3 border-r border-brutal-border pr-6">
            <span class="text-[9px] uppercase tracking-widest font-bold text-brutal-red">{{ currentOrgName }}</span>
            <PlanBadge :plan="currentOrgPlan" />
          </div>
          <router-link
            to="/org-settings"
            class="text-[9px] uppercase tracking-widest font-bold text-gray-500 hover:text-brutal-ink border-r border-brutal-border pr-6"
          >
            Settings
          </router-link>
          <div class="flex items-center gap-3">
            <label class="text-[9px] uppercase tracking-widest font-bold text-gray-500">Monitoring:</label>
            <select 
              v-model="currentMonitorExam" 
              @change="setMonitoringExam"
              class="border-2 border-brutal-ink bg-white text-brutal-ink px-4 py-2 text-xs font-bold uppercase cursor-pointer outline-none focus:ring-2 focus:ring-brutal-red"
            >
              <option value="" disabled>Select an Exam...</option>
              <option v-for="exam in activeExamsList" :key="exam.id" :value="exam.id">
                {{ exam.title }} (ID: {{ exam.id }})
              </option>
            </select>
          </div>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto relative z-10 p-8 pb-16">
        
        <DashboardOverview 
          v-if="activeTab === 'dashboard'" 
          :activeExamsCount="activeExamsCount"
          :liveCandidatesCount="liveCandidatesCount"
          :highRiskCount="highRiskCount"
          @change-tab="activeTab = $event" 
        />
        
        <CreateExam v-if="activeTab === 'create_exam'" @change-tab="handleExamCreated" />
        <ExamControl v-if="activeTab === 'exams'" :exams="exams" @change-tab="activeTab = $event" />
        <ReportsTab v-if="activeTab === 'reports'" :exams="exams" />
        <UserDirectory v-if="activeTab === 'users'" @open-modal="openModal" />
        <LiveMonitor v-if="activeTab === 'live'" @open-modal="openModal" />

      </main>

      <div class="absolute bottom-4 right-8 z-30 pointer-events-none text-[9px] uppercase tracking-super-wide font-bold text-gray-500 bg-brutal-paper px-2 py-1">
          &copy; UMNG
      </div>

    </div>

    <div v-if="showModal && selectedUser" class="fixed inset-0 bg-brutal-dark/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="bg-brutal-paper w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl border border-brutal-border">
        
        <div class="flex justify-between items-center p-6 border-b border-brutal-border bg-white">
          <div>
            <h2 class="text-2xl font-medium tracking-tight text-brutal-ink">{{ selectedUser.name }} <span class="text-sm font-normal text-gray-500 ml-2">ID: {{ selectedUser.id || selectedUser.username }}</span></h2>
            <p class="text-[9px] uppercase tracking-widest font-semibold text-brutal-red mt-1">
             • Total Violations: {{ selectedUser.totalViolations || 0 }}
            </p>
          </div>
          <button @click="closeModal" class="w-8 h-8 flex items-center justify-center border border-brutal-border hover:bg-brutal-ink hover:text-white transition-colors">X</button>
        </div>

        <div class="flex-1 overflow-y-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="flex flex-col gap-6">
            <div class="bg-white border border-brutal-border p-5">
              <h3 class="text-[9px] uppercase tracking-wide-ish font-semibold text-gray-500 mb-4">Violation Engine Breakdown</h3>
              <div class="space-y-2 text-sm font-medium tracking-tight">
                <div v-for="(count, type) in selectedUser.breakdown" :key="type" class="flex justify-between items-center py-2 border-b border-brutal-border/30 last:border-0">
                  <span class="text-brutal-ink">{{ type }}</span>
                  <span class="bg-gray-100 px-2 py-1 text-[10px] font-bold" :class="count > 0 ? 'text-brutal-red' : 'text-gray-500'">{{ count }}</span>
                </div>
              </div>
            </div>
            <button @click="clearUserViolations(selectedUser.username)" class="w-full bg-brutal-ink text-white py-4 text-[10px] uppercase tracking-super-wide font-bold hover:bg-gray-800 transition-colors">Clear Violations</button>
            <button class="w-full bg-brutal-red text-white py-4 text-[10px] uppercase tracking-super-wide font-bold hover:bg-brutal-ink transition-colors">Terminate Exam</button>
          </div>

          <div class="md:col-span-2 flex flex-col">
            <h3 class="text-[9px] uppercase tracking-wide-ish font-semibold text-gray-500 mb-4">Visual Proof / Timeline</h3>
            <div class="grid grid-cols-1 gap-4 overflow-y-auto">
              <div v-for="(shot, index) in selectedUser.screenshots" :key="index" class="bg-white border border-brutal-border flex flex-col sm:flex-row">
                <div class="w-full sm:w-48 h-32 bg-brutal-ink relative flex items-center justify-center overflow-hidden">
                  <img :src="shot.image_url" />
                  <div v-if="shot.critical" class="absolute inset-0 border-2 border-brutal-red shadow-[inset_0_0_20px_rgba(239,63,35,0.5)]"></div>
                </div>
                <div class="p-4 flex-1">
                  <div class="flex justify-between items-start mb-2">
                    <span class="text-[10px] uppercase tracking-widest font-bold text-brutal-red">{{ shot.type }}</span>
                    <span class="text-[9px] uppercase tracking-widest font-semibold text-gray-500">{{ shot.time }}</span>
                  </div>
                  <p class="text-sm font-medium tracking-tight text-brutal-ink">{{ shot.description || 'System flagged an anomaly.' }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import api, { logout as apiLogout } from '@/services/api';

// component Imports
import DashboardOverview from '../components/DashboardOverview.vue';
import CreateExam from '../components/CreateExamForm.vue';
import ExamControl from '../components/ExamControl.vue';
import ReportsTab from '../components/ReportsTab.vue';
import UserDirectory from '../components/UserDirectory.vue';
import LiveMonitor from '../components/LiveMonitor.vue';
import PlanBadge from '../components/PlanBadge.vue';

const router = useRouter();

const getCurrentExamId = () => {
  return localStorage.getItem("active_exam_id");
};

// Global Parent State
const activeTab = ref('dashboard');
const showModal = ref(false);
const selectedUser = ref(null);
const adminName = ref('Admin');
const currentOrgName = ref(localStorage.getItem('org_name') || '');
const currentOrgPlan = ref(localStorage.getItem('org_plan') || 'free');

// DRF Backend State
const exams = ref([]);
const liveCandidatesCount = ref(0);
const highRiskCount = ref(0);
let liveStatsInterval = null;

const currentMonitorExam = ref(localStorage.getItem("active_exam_id") || "");

const activeExamsList = computed(() => {
  return exams.value.filter(e => e.status === 'Active');
});

const setMonitoringExam = () => {
  if (currentMonitorExam.value) {
    localStorage.setItem("active_exam_id", currentMonitorExam.value);
    
    fetchDashboardStats(); 
    
    if (activeTab.value === 'live') {
      activeTab.value = 'dashboard';
      setTimeout(() => { activeTab.value = 'live'; }, 50);
    }
  }
};

const fetchExams = async () => {
  try {
    const response = await api.get(`admin/exam/list/`);
    const data = response.data;
    
    exams.value = data.map(exam => ({
      ...exam, 
      status: exam.is_active === true ? 'Active' : 'Disabled',
      date: exam.start_time ? new Date(exam.start_time).toISOString().split('T')[0] : 'No Date'
    }));
  } catch (error) { 
    console.error("Exams load failed:", error); 
  }
};

const activeExamsCount = computed(() => exams.value.filter(e => e.status === 'Active').length);

// ping function for updating the live user in dashboard 
const fetchDashboardStats = async () => {
  try {
    const examId = localStorage.getItem("active_exam_id");

    if (!examId){
      console.warn("No active exam id found");
      return;
    } 

    const response = await api.get(`admin/exam/${examId}/live/`);
    const data = response.data;
    console.log("LIVE DASHBOARD DATA:", data);

    liveCandidatesCount.value =
      data.filter(u => u.status === 'active').length;

    highRiskCount.value =
      data.filter(u => u.violations_count > 0 || u.risk_score >= 10).length;

  } 
  catch (error) {
    console.error("Stats load failed:", error);
  }
};

const startPolling = () => {
  if (!liveStatsInterval) {
    liveStatsInterval = setInterval(fetchDashboardStats, 10000);
  }
};

const stopPolling = () => {
  if (liveStatsInterval) {
    clearInterval(liveStatsInterval);
    liveStatsInterval = null;
  }
};

watch(activeTab, (newTab) => {
  if (newTab === 'dashboard' || newTab === 'live') {
    startPolling();
  } else {
    stopPolling();
  }
});

onMounted(() => {
    window.addEventListener("exam-started", fetchDashboardStats);

    if (!localStorage.getItem("access_token")) {
     router.push("/login");
      return;
    }

  const storedName = localStorage.getItem("username");
  if (storedName) adminName.value = storedName;
  currentOrgPlan.value = localStorage.getItem('org_plan') || 'free';
  fetchExams();
  fetchDashboardStats();
  
  if (activeTab.value === 'dashboard' || activeTab.value === 'live') {
    startPolling();
  }
});

onUnmounted(() => {
  window.removeEventListener("exam-started", fetchDashboardStats);
  stopPolling();
});

const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>' },
  { id: 'live', label: 'Live Monitor', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>' },
  { id: 'exams', label: 'Exam Control', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>' },
  { id: 'reports', label: 'Reports', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>' },
  { id: 'users', label: 'Users', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>' },
];

const handleExamCreated = (tabId) => {
  activeTab.value = tabId;
  if (tabId === 'exams') fetchExams();
};

const openModal = async (user) => {
  selectedUser.value = { ...user, breakdown: {}, screenshots: [] };
  showModal.value = true;
  try {
    const target = user.username || user.id;
    const response = await api.get(`admin/user/${target}/`);
    const data = response.data;
    
    selectedUser.value.breakdown = data.breakdown || {};
    selectedUser.value.totalViolations = Object.values(selectedUser.value.breakdown)
    .reduce((sum, val) => sum + Number(val || 0), 0);
    selectedUser.value.screenshots = (data.screenshots || []).map(shot => ({
      id: shot.id, type: shot.violation_type || 'SYSTEM_FLAG',
      time: new Date(shot.timestamp).toLocaleTimeString(),
      image_url: shot.image_url, critical: true 
    }));
  } catch (e) { 
    console.error("User details failed:", e); 
  }
};

const closeModal = () => { showModal.value = false; selectedUser.value = null; };

const clearUserViolations = async (username) => {
  if (!username) return;
  try {
    await api.post(`admin/user/${username}/clear/`);
    selectedUser.value.totalViolations = 0;
    alert("Cleared.");
  } catch (e) { 
    console.error("Clear failed:", e); 
  }
};

const logout = async () => {
  await apiLogout();
  router.push("/login"); 
};
</script>