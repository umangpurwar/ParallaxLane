<template>
  <div class="relative w-full h-screen overflow-hidden bg-brutal-dark font-sans text-brutal-ink">
    
    <div class="fixed inset-0 z-0 bg-brutal-maroon overflow-hidden opacity-50">
        <div class="absolute top-[-10%] left-[0%] w-[80%] h-[80%] bg-brutal-glow1 rounded-full mix-blend-screen filter blur-[140px] opacity-40"></div>
        <div class="absolute bottom-[-10%] right-[-10%] w-[70%] h-[70%] bg-brutal-glow2 rounded-full mix-blend-screen filter blur-[150px] opacity-50"></div>
    </div>

    <div class="relative z-10 w-[96vw] max-w-[1800px] h-[94vh] mx-auto mt-[3vh] bg-brutal-paper shadow-2xl flex flex-col overflow-hidden">
      
      <div v-if="!isSecureMode" class="absolute inset-0 z-[100] bg-brutal-paper flex flex-col items-center justify-center p-8">
        <h2 class="text-4xl font-medium tracking-tighter text-brutal-ink mb-4">Secure Environment Required</h2>
        <p class="text-[10px] uppercase tracking-widest font-semibold text-gray-500 mb-8 text-center max-w-md">
          ParallaxLane requires Fullscreen and Camera access. Leaving fullscreen, switching tabs, or opening external assistants will be logged as violations.
        </p>
        <div class="text-center mb-6">
        <p class="text-lg font-bold text-brutal-ink">
          {{ exam?.title }}
          </p>
          <p class="text-xs text-gray-600 mt-2 max-w-md">
          {{ exam?.description }}
          </p>
        </div>
        <button @click="enterSecureMode" class="bg-brutal-red text-white px-12 py-5 text-[12px] uppercase tracking-super-wide font-bold hover:bg-brutal-ink transition-colors shadow-2xl">
          Initialize Secure Mode
        </button>
      </div>

      <div v-if="showSubmitModal" class="absolute inset-0 z-[110] bg-brutal-dark/80 backdrop-blur-sm flex items-center justify-center p-8">
        <div class="bg-brutal-paper border border-brutal-border p-8 max-w-md w-full shadow-2xl flex flex-col">
          <h3 class="text-2xl font-medium tracking-tight text-brutal-ink mb-4">Confirm Submission</h3>
          <p class="text-sm font-medium text-gray-800 mb-8">
            Are you sure you want to submit your exam? You cannot undo this action.
          </p>
          <div class="flex gap-4">
            <button @click="showSubmitModal = false" class="flex-1 border border-brutal-ink text-brutal-ink py-4 text-[10px] uppercase tracking-super-wide font-bold hover:bg-brutal-ink hover:text-white transition-colors">
              Cancel
            </button>
            <button @click="executeSubmit" class="flex-1 bg-brutal-red text-white py-4 text-[10px] uppercase tracking-super-wide font-bold hover:bg-brutal-ink transition-colors">
              Submit Exam
            </button>
          </div>
        </div>
      </div>

      <div v-if="showLeaveWarningModal" class="absolute inset-0 z-[120] bg-brutal-dark/90 backdrop-blur-md flex items-center justify-center p-8">
        <div class="bg-brutal-paper border-4 border-brutal-ink p-8 max-w-md w-full shadow-[8px_8px_0px_0px_rgba(239,63,35,1)] flex flex-col text-center">
          <h3 class="text-3xl font-black tracking-tighter text-brutal-red mb-4 uppercase italic">Security Alert</h3>
          <p class="text-sm font-bold text-gray-800 mb-8 leading-tight">
            You are attempting to leave the secure exam environment. Leaving now will <span class="text-brutal-red">automatically submit</span> your current answers and terminate your session.
          </p>
          <div class="flex flex-col gap-3">
            <button @click="cancelLeave" class="w-full border-2 border-brutal-ink text-brutal-ink py-4 text-[10px] uppercase tracking-super-wide font-black hover:bg-brutal-ink hover:text-white transition-colors">
              Return to Exam
            </button>
            <button @click="confirmLeaveAndSubmit" class="w-full bg-brutal-red text-white py-4 text-[10px] uppercase tracking-super-wide font-black hover:bg-brutal-ink transition-colors">
              Leave & Submit
            </button>
          </div>
        </div>
      </div>

      <transition name="fade">
        <div v-if="errorMessage || statusMessage" class="absolute top-0 left-0 w-full z-50 p-4 pointer-events-none">
          <div v-if="errorMessage" class="bg-brutal-ink text-white p-4 font-bold tracking-widest uppercase text-center text-sm shadow-xl mt-2 pointer-events-auto">
             {{ errorMessage }}
          </div>
          <div v-if="statusMessage" class="bg-emerald-600 text-white p-4 font-bold tracking-widest uppercase text-center text-sm shadow-xl mt-2 pointer-events-auto">
             {{ statusMessage }}
          </div>
        </div>
      </transition>

      <header class="h-[12%] min-h-[80px] flex border-b border-brutal-border relative z-20 bg-brutal-paper">
        <div class="w-[20%] lg:w-[15%] h-full flex items-center justify-center font-bold tracking-super-wide text-[13px] border-r border-brutal-border">
          PARALLAXLANE
        </div>
        
        <div class="flex-1 h-full flex items-center justify-between px-8 border-r border-brutal-border">
          <div>
            <p v-if="currentOrg" class="text-[9px] uppercase tracking-widest font-bold text-brutal-red mb-1">{{ currentOrg }}</p>
            <h1 class="text-xl md:text-2xl font-medium tracking-tight truncate">{{ exam?.title || 'Loading Exam...' }}</h1>
            <div class="h-5 flex items-center mt-1 gap-4">
              <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500">
                Violations Logged: <span :class="violationCount > 0 ? 'text-brutal-red font-bold' : ''">{{ violationCount }}</span>
              </p>
              <transition name="fade">
                <p v-if="warningMessage" class="text-[9px] uppercase tracking-widest font-bold text-brutal-ink">
                  {{ warningMessage }}
                </p>
              </transition>
            </div>
          </div>
          <div class="text-right">
            <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500 mb-1">Time Remaining</p>
            <p class="text-3xl font-medium tracking-tighter" :class="timeLeft < 300 ? 'text-brutal-red animate-pulse' : 'text-brutal-ink'">
              {{ formatTime() }}
            </p>
          </div>
        </div>

        <div class="w-[20%] h-full flex">
          <button @click="confirmSubmit" class="w-full h-full bg-brutal-red hover:bg-brutal-ink text-white flex items-center justify-center text-[11px] uppercase tracking-super-wide font-bold transition-colors">
            End & Submit
          </button>
        </div>
      </header>

      <main class="flex-1 flex overflow-hidden relative z-10">
        
        <div class="flex-1 flex flex-col relative overflow-y-auto border-r border-brutal-border bg-brutal-paper">
          <div v-if="exam && exam.questions && exam.questions.length > 0" class="flex-1 flex flex-col p-8 md:p-16 max-w-5xl mx-auto w-full">
            
            <p class="text-[10px] uppercase tracking-super-wide font-bold text-brutal-red mb-6">
              Question {{ currentQuestionIndex + 1 }} of {{ exam.questions.length }}
            </p>

            <h2 class="text-2xl md:text-3xl lg:text-4xl font-medium tracking-tight leading-[1.3] text-brutal-ink mb-12">
              {{ currentQuestion.text }}
            </h2>

            <div class="grid grid-cols-1 gap-4 mt-auto mb-12">
              <label 
                v-for="(option, optIndex) in (currentQuestion.options || [])" :key="option.id"
                class="relative border-2 p-6 flex items-center cursor-pointer transition-all duration-200 group"
                :class="answers[currentQuestion.id] === option.id ? 'border-brutal-red bg-brutal-red/5' : 'border-brutal-border hover:border-brutal-ink bg-white'"
              >
                <input 
                  type="radio" 
                  :name="String(currentQuestion.id)" 
                  :value="option.id" 
                  :checked="answers[currentQuestion.id] === option.id"
                  @click.prevent="toggleAnswer(currentQuestion.id, option.id)"
                  class="sr-only" 
                />
                <div class="w-8 h-8 rounded-full border-2 flex items-center justify-center mr-6 font-bold text-sm uppercase transition-colors"
                     :class="answers[currentQuestion.id] === option.id ? 'border-brutal-red text-brutal-red' : 'border-brutal-border text-gray-400 group-hover:border-brutal-ink group-hover:text-brutal-ink'">
                  {{ String.fromCharCode(65 + optIndex) }}
                </div>
                <span class="text-lg font-medium" :class="answers[currentQuestion.id] === option.id ? 'text-brutal-red' : 'text-brutal-ink'">
                  {{ option.text }}
                </span>
              </label>
            </div>

            <div class="flex justify-between items-center mt-auto border-t border-brutal-border pt-8">
              <button 
                @click="prevQuestion" 
                :disabled="currentQuestionIndex === 0"
                class="px-8 py-4 border border-brutal-ink text-[10px] uppercase tracking-widest font-bold hover:bg-brutal-ink hover:text-white transition-colors disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-brutal-ink disabled:cursor-not-allowed"
              >
                &larr; Previous
              </button>
              
              <button 
                v-if="currentQuestionIndex < exam.questions.length - 1"
                @click="nextQuestion" 
                class="px-8 py-4 bg-brutal-ink text-white text-[10px] uppercase tracking-widest font-bold hover:bg-brutal-red transition-colors"
              >
                Next &rarr;
              </button>
              <button 
                v-else
                @click="confirmSubmit" 
                class="px-8 py-4 bg-brutal-red text-white text-[10px] uppercase tracking-widest font-bold hover:bg-brutal-ink transition-colors"
              >
                Review & Submit
              </button>
            </div>

          </div>
          
          <div v-else-if="!exam" class="flex-1 flex items-center justify-center">
            <p class="text-[10px] uppercase tracking-widest font-bold animate-pulse">Initializing Exam Environment...</p>
          </div>
        </div>

        <div class="w-[300px] lg:w-[350px] flex flex-col bg-brutal-paper relative">
          
          <div class="h-[250px] border-b border-brutal-border relative bg-black flex flex-col justify-end p-4">
            <video ref="videoRef" autoplay playsinline muted class="absolute inset-0 w-full h-full object-cover opacity-80"></video>
            <div class="relative z-10 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-brutal-red animate-pulse"></span>
              <span class="text-[9px] uppercase tracking-widest font-bold text-white drop-shadow-md">ProctorGuard Active</span>
            </div>
            <div class="absolute inset-0 pointer-events-none border-[10px] border-brutal-dark/20"></div>
          </div>

          <div class="flex-1 overflow-y-auto p-6 flex flex-col pb-12">
            <h3 class="text-[9px] uppercase tracking-wide-ish font-semibold text-gray-500 mb-6">Question Navigator</h3>
            
            <div v-if="exam && exam.questions" class="grid grid-cols-5 gap-2 mb-8">
              <button 
                v-for="(q, index) in exam.questions" :key="q.id"
                @click="goToQuestion(index)"
                class="w-full aspect-square flex items-center justify-center text-sm font-bold border transition-all duration-200"
                :class="[
                  currentQuestionIndex === index ? 'ring-2 ring-offset-2 ring-offset-brutal-paper ring-brutal-ink' : '',
                  getQuestionStatusClass(q.id, index)
                ]"
              >
                {{ index + 1 }}
              </button>
            </div>

            <div class="mt-auto space-y-3 pt-6 border-t border-brutal-border/50">
              <div class="flex items-center gap-3">
                <div class="w-4 h-4 bg-brutal-red border border-brutal-red"></div>
                <span class="text-[10px] uppercase tracking-widest font-semibold text-gray-600">Attempted</span>
              </div>
              <div class="flex items-center gap-3">
                <div class="w-4 h-4 bg-brutal-ink border border-brutal-ink"></div>
                <span class="text-[10px] uppercase tracking-widest font-semibold text-gray-600">Seen (Unanswered)</span>
              </div>
              <div class="flex items-center gap-3">
                <div class="w-4 h-4 bg-transparent border border-brutal-border"></div>
                <span class="text-[10px] uppercase tracking-widest font-semibold text-gray-600">Not Visited</span>
              </div>
            </div>

          </div>
        </div>

      </main>

      <div class="absolute bottom-4 right-6 z-30 pointer-events-none text-[9px] uppercase tracking-super-wide font-bold text-gray-500">
          &copy; UMNG
      </div>

    </div>
  </div>
</template>

<script setup>
const clearExamLocalState = () => {
  const examId = route.params.id
  localStorage.removeItem("attempt_id")
  localStorage.removeItem("active_exam_id")
  if (examId) {
    localStorage.removeItem(`exam_state_${examId}`)
  }
}

const handleExamTermination = (message = "Exam has been terminated by admin") => {
  errorMessage.value = message;

  cleanup(); // stop camera, timers, heartbeat

  setTimeout(() => {
    clearExamLocalState()
    router.push("/dashboard");
  }, 2000);
};

import { ref, onMounted, onUnmounted, nextTick, computed, watch } from "vue"
import { useRoute, useRouter, onBeforeRouteLeave } from "vue-router" 
import api from "../services/api"

const route = useRoute()
const router = useRouter()

const exam = ref(null)
const answers = ref({})
const timeLeft = ref(0)
const currentOrg = ref("") // NEW: Organisation state

const violationCount = ref(0)
const warningMessage = ref("")
const errorMessage = ref("")
const statusMessage = ref("")

const showSubmitModal = ref(false)
const showLeaveWarningModal = ref(false) 

const videoRef = ref(null)

let timer = null
let mediaStream = null
let cameraInterval = null
let heartbeatInterval = null

// Initialize as null,  set this AFTER the camera is allowed
const attemptId = ref(null) 
const violationCooldowns = {}

const isSecureMode = ref(false)
let isAutoSubmitting = false
let pendingRoute = null

// routing logic
onBeforeRouteLeave((to, from, next) => {
  if (isAutoSubmitting || !isSecureMode.value || showSubmitModal.value) {
    next()
  } else {
    showLeaveWarningModal.value = true
    pendingRoute = to
    next(false) 
  }
})

const cancelLeave = () => {
  showLeaveWarningModal.value = false
  pendingRoute = null
}

const confirmLeaveAndSubmit = async () => {
  showLeaveWarningModal.value = false
  isAutoSubmitting = true 
  await submitExam()
  
  if (pendingRoute) {
    router.push(pendingRoute.path)
  } else {
    router.push("/dashboard")
  }
}

// pagination
const currentQuestionIndex = ref(0)
const visitedQuestions = ref(new Set([0]))

const currentQuestion = computed(() => {
  if (!exam.value || !exam.value.questions) return null
  return exam.value.questions[currentQuestionIndex.value]
})

const goToQuestion = (index) => {
  currentQuestionIndex.value = index
  visitedQuestions.value.add(index)
  saveExamState()   // force persist
}

const nextQuestion = () => {
  if (currentQuestionIndex.value < exam.value.questions.length - 1) {
    goToQuestion(currentQuestionIndex.value + 1)
  }
}

const prevQuestion = () => {
  if (currentQuestionIndex.value > 0) {
    goToQuestion(currentQuestionIndex.value - 1)
  }
}

const getQuestionStatusClass = (questionId, index) => {
  const isAnswered = answers.value[questionId] !== undefined && answers.value[questionId] !== ""
  const isVisited = visitedQuestions.value.has(index)

  if (isAnswered) return 'bg-brutal-red border-brutal-red text-white'
  else if (isVisited) return 'bg-brutal-ink border-brutal-ink text-white'
  else return 'bg-transparent border-brutal-border text-brutal-ink hover:border-brutal-ink'
}

// core logic

// saving the data in memory so after reloaded it does not get lost
const saveExamState = () => {
  const examId = route.params.id;

  const state = {
    answers: answers.value,
    currentQuestionIndex: currentQuestionIndex.value,
    visitedQuestions: Array.from(visitedQuestions.value),
    timeLeft: timeLeft.value
  };

  localStorage.setItem(`exam_state_${examId}`, JSON.stringify(state));
};


watch(answers, saveExamState, { deep: true });
watch(currentQuestionIndex, saveExamState);
watch(timeLeft, saveExamState);

const fetchExamData = async () => {
  try {
    const examId = route.params.id
    const res = await api.get(`exams/${examId}/`)
    exam.value = res.data?.data || res.data

    // NEW: ORG CONSISTENCY CHECK
    const storedOrgSlug = localStorage.getItem("org_slug")
    const examOrg = exam.value.organisation || exam.value.org_slug
    
    if (examOrg && storedOrgSlug && examOrg !== storedOrgSlug) {
      errorMessage.value = "Organisation mismatch. Returning to dashboard."
      setTimeout(() => {
        router.push("/dashboard")
      }, 2000)
      return
    }

    const saved = localStorage.getItem(`exam_state_${examId}`)

    if (saved) {
      const parsed = JSON.parse(saved)

      answers.value = parsed.answers || {}
      currentQuestionIndex.value = parsed.currentQuestionIndex || 0
      visitedQuestions.value = new Set(parsed.visitedQuestions || [0])
      timeLeft.value = parsed.timeLeft ?? exam.value.duration * 60
    } else {
      timeLeft.value = exam.value.duration * 60
    }

  } catch (error) {
    errorMessage.value = "Failed to load exam data. Please return to dashboard."
  }
}

// Step 2: The User clicks "Initialize Secure Mode"
const enterSecureMode = async () => {
  try {
    // NEW: OPTIONAL SAFETY (LIGHT)
    if (!localStorage.getItem("org_slug")) {
      errorMessage.value = "No organisation context found. Returning to dashboard."
      setTimeout(() => router.push("/dashboard"), 2000)
      return
    }

    // 1. Ask for permission first
    console.log("STEP 1: before webcam");
    await startWebcam();
    
    // 2. If permission is allowed, force Fullscreen
  
    const docEl = document.documentElement;
    if (docEl.requestFullscreen) {
        console.log("STEP 2: after webcam, before fullscreen");
      await docEl.requestFullscreen();
      console.log("STEP 3: after fullscreen, before API");
    } else if (docEl.webkitRequestFullscreen) {
      await docEl.webkitRequestFullscreen();
    } else if (docEl.msRequestFullscreen) {
      await docEl.msRequestFullscreen();
    }
    
    
    const examId = route.params.id;
    console.log("SETTING EXAM ID:", examId);
    
    // 3. Create the Database Record (Start Attempt)
    try {
      localStorage.setItem("active_exam_id", examId);  
      window.dispatchEvent(new Event("exam-started"));
      const startRes = await api.post(`exams/${examId}/start/`);
      console.log("STEP 4: after API");
      if (startRes.data && startRes.data.attempt_id) {
        attemptId.value = startRes.data.attempt_id;
        localStorage.setItem("attempt_id", startRes.data.attempt_id);
      }
    } catch (startErr) {
      console.warn("Failed to log start attempt with backend.", startErr);
    }

    // 4. Start Exam Environment
    isSecureMode.value = true;
    visitedQuestions.value.add(0); 
    startTimer();
    monitorCamera();
    
    // 5. Start Heartbeat
    pingBackend(); 
    heartbeatInterval = setInterval(pingBackend, 5000); 
    
  } catch (err) {
    console.error("Secure mode initialization failed:", err); // Added this so you can see exact errors in console
    errorMessage.value = "Camera access denied. You cannot take this exam without a camera.";
    setTimeout(() => (errorMessage.value = ""), 4000);
  }
}

const startTimer = () => {
  timer = setInterval(() => {
    if (timeLeft.value > 0) {
      timeLeft.value--;
    } else {
      if (!isSubmitting) {
        submitExam();
      }
    }
  }, 1000);
}

const formatTime = () => {
  const m = Math.floor(timeLeft.value / 60)
  const s = timeLeft.value % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

const pingBackend = async () => {
  if (!isSecureMode.value || !attemptId.value) return; 

  try {
    const response = await api.post(`monitoring/heartbeat/`, { 
      attempt_id: attemptId.value 
    });

    if (response.data && response.data.take_screenshot) {
      console.log("📸 Admin requested a live screenshot!");
      captureScreenshot();
    }

  } catch (error) {
    if (error.response?.status === 403) {
      handleExamTermination(error.response.data?.error);
    } else {
      console.warn("Heartbeat failed, retrying on next tick...");
    }
  }
}

const handleFullscreenChange = () => {
  if (!document.fullscreenElement && isSecureMode.value && !showSubmitModal.value && !showLeaveWarningModal.value) {
    logViolation("ESC_FULLSCREEN");
    isSecureMode.value = false;
  }
}

const confirmSubmit = () => {
  showSubmitModal.value = true;
}

const executeSubmit = () => {
  showSubmitModal.value = false;
  submitExam();
}

let isSubmitting=false
const submitExam = async () => {
  
  if (isSubmitting) return;
  isSubmitting = true;

  cleanup()
  isAutoSubmitting = true; 

  try {
    statusMessage.value = "Submitting exam securely..."

    const examId = route.params.id

    
    if (!examId) {
      console.error("Exam ID missing — stopping submit");
      return;
    }

    
    clearExamLocalState()
    const res = await api.post(`exams/${examId}/submit/`, {
      answers: answers.value
    })

    statusMessage.value = `Exam Submitted! Score: ${res.data.points_scored}/${res.data.total_points}`
    setTimeout(() => router.push("/dashboard"), 3000)

  } catch (error) {
  if (error.response?.status === 403) {
    handleExamTermination(error.response.data?.error);
    return;
  }

  console.error("SUBMISSION ERROR:", error.response?.data || error.message);
  statusMessage.value = "Submission failed. Check console for details."
  setTimeout(() => router.push("/dashboard"), 3000)
}
}

// screenshot
const captureScreenshot = () => {
  if (!videoRef.value || !attemptId.value) return;

  const canvas = document.createElement("canvas");
  canvas.width = videoRef.value.videoWidth;
  canvas.height = videoRef.value.videoHeight;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(videoRef.value, 0, 0);

canvas.toBlob(async (blob) => {
  const formData = new FormData();
  formData.append("attempt_id", attemptId.value);
  formData.append("image", blob, "screenshot.png");

  await api.post("monitoring/screenshot/", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
}, "image/png", 0.6);
};

const VIOLATION_TYPE_MAP = {
  TAB_SWITCH: 'tab_switch',
  WINDOW_FOCUS_LOST: 'window_blur',
  ESC_FULLSCREEN: 'window_blur',
  CAMERA_OFF: 'no_face',
  DEVTOOLS: 'suspicious_movement',
  COPY_PASTE: 'copy_paste',
}

// violation
const logViolation = async (type) => {
  if (!isSecureMode.value) return;

  const apiType = VIOLATION_TYPE_MAP[type] || type.toLowerCase()
  const now = Date.now();
  const cooldownKey =
    (type === 'TAB_SWITCH' || type === 'WINDOW_FOCUS_LOST')
      ? 'FOCUS_GROUP'
      : type;

  if (violationCooldowns[cooldownKey] && now - violationCooldowns[cooldownKey] < 2000) return;
  violationCooldowns[cooldownKey] = now;

  violationCount.value += 1;
  warningMessage.value = type.replace(/_/g, ' ');
  setTimeout(() => (warningMessage.value = ""), 4000);

  if (!attemptId.value) return;

  try {
    captureScreenshot();

    let res;
    try {
      res = await api.post("monitoring/log/", {
        attempt_id: attemptId.value,
        type: apiType,
        severity: 1
      });
    } catch (error) {
      if (error.response?.status === 403) {
        handleExamTermination(error.response.data?.error);
        return;
      } else {
        console.error("Failed to log violation", error);
        return;
      }
    }

    if (res.data && res.data.violations !== undefined) {
      violationCount.value = res.data.violations;
    }

    if (res.data && res.data.state === "terminated") {
      errorMessage.value = "EXAM TERMINATED DUE TO MULTIPLE VIOLATIONS.";
      setTimeout(() => submitExam(), 2000);
    }

  } catch (err) {
    console.error("Failed to log violation", err);
  }
};
const startWebcam = async () => {
  // request full screen
  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: {
      displaySurface: "monitor" // force full monitor
    },
    audio: false
  });

  // reject if user selects tab/window
  const track = stream.getVideoTracks()[0];
  const settings = track.getSettings();

  if (settings.displaySurface !== "monitor") {
    track.stop();
    throw new Error("Please select entire screen (monitor), not tab/window");
  }

  mediaStream = stream;

  await nextTick();
  if (videoRef.value) {
    videoRef.value.srcObject = stream;
    await videoRef.value.play();
  }
};

const monitorCamera = () => {
  cameraInterval = setInterval(async () => {
    if (!mediaStream || !isSecureMode.value) return
    const v = mediaStream.getVideoTracks()[0]
    if (!v || v.readyState !== "live" || !v.enabled) {
      logViolation("CAMERA_OFF")
      // Stop trying to restart it constantly if they unplugged it, just log it.
    }
  }, 2000)
}

const handleTab = () => { if (document.hidden && isSecureMode.value) logViolation("TAB_SWITCH") }
const handleBlur = () => { if (isSecureMode.value) logViolation("WINDOW_FOCUS_LOST") }
const handleKey = (e) => {
  if (!isSecureMode.value) return;
  if (e.key === "Escape") logViolation("ESC_FULLSCREEN")
  if (e.key === "F12") logViolation("DEVTOOLS")
}

const cleanup = () => {
  clearInterval(timer)
  clearInterval(cameraInterval)
  clearInterval(heartbeatInterval)
  
  document.removeEventListener("visibilitychange", handleTab)
  document.removeEventListener("keydown", handleKey)
  window.removeEventListener("blur", handleBlur)
  document.removeEventListener("fullscreenchange", handleFullscreenChange)

  if (document.fullscreenElement) document.exitFullscreen().catch(() => {})
  if (mediaStream) mediaStream.getTracks().forEach(t => t.stop())
}

onMounted(() => {
  document.addEventListener('contextmenu', event => event.preventDefault());
  
  // NEW: LOAD CURRENT ORG
  const storedOrgName = localStorage.getItem("org_name")
  if (storedOrgName) {
    currentOrg.value = storedOrgName
  }
  
  // Only fetch the text data on mount. do not start the exam attempt yet.
  fetchExamData()
  
  document.addEventListener("visibilitychange", handleTab)
  window.addEventListener("blur", handleBlur)
  document.addEventListener("keydown", handleKey)
  document.addEventListener("fullscreenchange", handleFullscreenChange)

  const savedAttempt = localStorage.getItem("attempt_id")

    if (savedAttempt) {
    attemptId.value = savedAttempt
}
})

onUnmounted(() => {
  document.removeEventListener('contextmenu', event => event.preventDefault());
  cleanup()
})

const toggleAnswer = (questionId, optionId) => {
  if (answers.value[questionId] === optionId) {
    delete answers.value[questionId];
  } else {
    answers.value[questionId] = optionId;
  }

  saveExamState();
};
</script>