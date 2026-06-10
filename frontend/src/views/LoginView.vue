<template>

   <div class="relative w-full h-screen overflow-hidden bg-brutal-dark font-sans">
    <div class="fixed inset-0 z-0 bg-brutal-maroon overflow-hidden">
        <div class="absolute top-[-10%] left-[0%] w-[80%] h-[80%] bg-brutal-glow1 rounded-full mix-blend-screen filter blur-[140px] opacity-70 animate-pulse"></div>
        <div class="absolute bottom-[-10%] right-[-10%] w-[70%] h-[70%] bg-brutal-glow2 rounded-full mix-blend-screen filter blur-[150px] opacity-80"></div>
    </div>

<transition name="reveal" appear>
  <div class="relative z-10 w-[92vw] max-w-[1600px] h-[90vh] mx-auto mt-[5vh] bg-brutal-paper shadow-2xl flex flex-col overflow-hidden">
    
    <div class="absolute inset-0 pointer-events-none z-10">
        <div class="grid-line-v left-[25%]"></div>
        <div class="grid-line-v left-[50%]"></div>
        <div class="grid-line-v left-[75%] hidden lg:block"></div>
        <div class="grid-line-h top-[20%]"></div>
    </div>

    <header class="absolute top-0 left-0 w-full h-[20%] flex z-20">
      <div class="w-[25%] h-full flex items-center justify-center font-bold tracking-super-wide text-[13px] text-black">
        PARALLAXLANE
      </div>

      <div class="w-[50%] h-full flex items-center px-8">
        <h1 class="text-[2rem] font-medium tracking-tighter text-brutal-ink">
          Log In
        </h1>
      </div>

      <div class="w-[25%] h-full flex items-center justify-end px-8">
        <router-link to="/" class="text-[9px] uppercase tracking-widest font-semibold text-gray-700 hover:text-brutal-red transition-colors pointer-events-auto">
            RETURN HOME
        </router-link>
      </div>
    </header>

    <main class="absolute top-[20%] bottom-0 left-0 w-full flex z-10">
        
        <div class="hidden lg:block w-[25%] h-full"></div>
        
        <div class="w-full md:w-[60%] lg:w-[50%] h-full flex flex-col justify-center px-8 sm:px-12 lg:px-24 pointer-events-auto border-r-0 lg:border-r border-brutal-border/30">
            
            <div class="flex flex-col gap-6 w-full max-w-md mx-auto">
                
                <div class="relative">
                    <input 
                        v-model="email" 
                        type="text" 
                        :placeholder="isOtpFlow ? 'EMAIL ADDRESS' : 'EMAIL'" 
                        class="w-full bg-transparent border-b-2 border-brutal-border py-3 text-brutal-ink font-medium tracking-widest text-[12px] placeholder-gray-500 focus:outline-none focus:border-brutal-red transition-colors"
                        :disabled="isLoading"
                    />
                </div>
                
                <div class="relative" v-if="!isOtpFlow">
                    <input 
                        v-model="password" 
                        type="password" 
                        placeholder="PASSWORD" 
                        class="w-full bg-transparent border-b-2 border-brutal-border py-3 text-brutal-ink font-medium tracking-widest text-[12px] placeholder-gray-500 focus:outline-none focus:border-brutal-red transition-colors"
                        :disabled="isLoading"
                    />
                </div>

                <div class="captcha-theme-wrapper p-1">
                    <CaptchaBox ref="captchaRef" @verified="captchaVerified = $event" />
                </div>

                <p v-if="errorMessage" class="text-[10px] uppercase tracking-widest font-bold text-brutal-red leading-tight">
                    {{ errorMessage }}
                </p>

                <button 
                    @click="handleMainAction" 
                    :disabled="!captchaVerified || isLoading"
                    class="mt-2 w-full py-4 text-[10px] uppercase tracking-super-wide font-bold transition-all duration-300"
                    :class="(captchaVerified && !isLoading) ? 'bg-brutal-ink hover:bg-brutal-red text-brutal-paper cursor-pointer' : 'bg-gray-300 text-gray-500 cursor-not-allowed'"
                >
                    {{ primaryButtonText }}
                </button>
            </div>
        </div>

        <div class="w-full md:w-[40%] lg:w-[25%] h-full flex flex-col justify-center px-8 sm:px-12 pointer-events-auto">
            <div class="flex flex-col gap-5 w-full max-w-xs mx-auto">
                
                <button 
                 @click="triggerGoogleLogin" 
                type="button" 
                class="flex items-center justify-center gap-3 w-full py-4 px-4 text-[10px] uppercase tracking-super-wide font-bold border-2 border-brutal-ink bg-transparent hover:bg-brutal-ink hover:text-brutal-paper transition-all duration-300 text-brutal-ink"
                :disabled="isLoading"
                  >
                <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M21.35 11.1h-9.18v2.98h5.26c-.23 1.25-1.4 3.67-5.26 3.67-3.17 0-5.75-2.62-5.75-5.85s2.58-5.85 5.75-5.85c1.8 0 3 .77 3.69 1.43l2.52-2.44C17.06 3.36 14.9 2.5 12.17 2.5 6.98 2.5 2.77 6.77 2.77 12s4.21 9.5 9.4 9.5c5.43 0 9.02-3.82 9.02-9.2 0-.62-.07-1.08-.16-1.5z"/>
                </svg>
                  Continue with Google
                  </button>
                <button 
                    @click="toggleOtpFlow" 
                    type="button"
                    class="flex items-center justify-center w-full py-4 px-4 border border-[#ccc] bg-[#f4f1ea] hover:bg-[#e8e4d9] transition-colors text-[10px] font-bold tracking-widest uppercase text-brutal-ink"
                    :disabled="isLoading"
                >
                    {{ isOtpFlow ? 'Use Password Login' : 'Login with OTP' }}
                </button>
                
                <div class="h-[1px] w-full bg-brutal-border/40 my-3"></div>
                
                <button 
                    @click="openForgotModal" 
                    type="button"
                    class="text-[10px] uppercase tracking-widest font-semibold text-gray-600 hover:text-brutal-red transition-colors text-center"
                >
                    Forgot Password?
                </button>

                <button 
                    @click="$router.push('/register')" 
                    type="button"
                    class="text-[10px] uppercase tracking-widest font-semibold text-gray-600 hover:text-brutal-red transition-colors text-center"
                >
                    New user? Register here
                </button>

            </div>
        </div>

    </main>

    <div class="absolute bottom-6 right-8 z-30 pointer-events-none text-[9px] uppercase tracking-super-wide font-bold text-gray-500">
        &copy; UMNG & KUSIK
    </div>
  </div>
</transition>

<!-- OTP LOGIN MODAL OVERLAY -->
<transition name="fade">
  <div v-if="showOtpModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-6 backdrop-blur-sm">
    <div class="max-w-md w-full bg-[#f5f5f5] text-[#1a1a1a] border-4 border-[#1a1a1a] p-10 flex flex-col items-center text-center shadow-[12px_12px_0px_0px_rgba(239,63,35,1)]">
      
      <h2 class="text-3xl font-black uppercase tracking-widest mb-4 border-b-2 border-[#1a1a1a] pb-4 w-full">Verify OTP</h2>
      <p class="text-sm font-bold mb-8 text-gray-700 leading-tight">
        Enter the 6-digit code sent to your email.
      </p>

      <div class="flex gap-2 mb-8">
        <input
          v-for="(digit, index) in otp"
          :key="'otp-'+index"
          ref="otpInputs"
          v-model="otp[index]"
          @input="handleOtpInput(index, $event)"
          @keydown="handleOtpKeydown(index, $event)"
          type="text"
          maxlength="1"
          class="w-10 h-14 sm:w-12 text-center text-2xl font-black bg-white border-2 border-[#1a1a1a] focus:outline-none focus:border-[#ef3f23] transition-colors"
        />
      </div>

      <p v-if="otpError" class="text-[10px] uppercase font-bold text-[#ef3f23] mb-4">{{ otpError }}</p>

      <button 
        @click="verifyOtp" 
        :disabled="otpLoading"
        class="w-full bg-[#1a1a1a] text-white py-4 text-[11px] uppercase tracking-[0.4em] font-black hover:bg-[#ef3f23] transition-all transform active:scale-95 border-b-4 border-r-4 border-gray-600 mb-4 disabled:opacity-50"
      >
        {{ otpLoading ? 'Verifying...' : 'Verify' }}
      </button>

      <div class="flex w-full justify-between gap-4">
        <button 
        @click="resendOtp"
        :disabled="resendTimer > 0"
        class="flex-1 border-2 border-[#1a1a1a] py-3 text-[9px] uppercase tracking-widest font-bold transition-colors"
        :class="resendTimer > 0 
        ? 'opacity-50 cursor-not-allowed' 
        : 'hover:bg-[#1a1a1a] hover:text-white'"
        >
        {{ resendTimer > 0 ? `Resend in ${resendTimer}s` : 'Resend OTP' }}
        </button>
        <button @click="closeOtpModal" class="flex-1 border-2 border-transparent text-[#ef3f23] hover:text-red-700 py-3 text-[9px] uppercase tracking-widest font-bold transition-colors">
          Cancel
        </button>
      </div>

    </div>
  </div>
</transition>



<!-- FORGOT PASSWORD MODAL OVERLAY -->
<transition name="fade">
  <div v-if="showForgotModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-6 backdrop-blur-sm">
    <div class="max-w-md w-full bg-[#f5f5f5] text-[#1a1a1a] border-4 border-[#1a1a1a] p-10 flex flex-col items-center text-center shadow-[12px_12px_0px_0px_rgba(239,63,35,1)]">
      
      <h2 class="text-3xl font-black uppercase tracking-widest mb-4 border-b-2 border-[#1a1a1a] pb-4 w-full">Reset Password</h2>
      
      <!-- Step 1: Email -->
      <template v-if="forgotStep === 'email'">
        <p class="text-sm font-bold mb-8 text-gray-700 leading-tight">
          Enter your email to receive a reset code.
        </p>
        
        <input 
            v-model="forgotEmail" 
            type="email" 
            placeholder="EMAIL ADDRESS" 
            class="w-full bg-transparent border-b-2 border-[#1a1a1a] py-3 text-brutal-ink font-medium tracking-widest text-[12px] placeholder-gray-500 focus:outline-none focus:border-[#ef3f23] transition-colors mb-6 text-center"
            :disabled="forgotLoading"
        />

        <p v-if="forgotError" class="text-[10px] uppercase font-bold text-[#ef3f23] mb-4">{{ forgotError }}</p>

        <button 
          @click="sendForgotOtp" 
          :disabled="forgotLoading"
          class="w-full bg-[#1a1a1a] text-white py-4 text-[11px] uppercase tracking-[0.4em] font-black hover:bg-[#ef3f23] transition-all transform active:scale-95 border-b-4 border-r-4 border-gray-600 mb-4 disabled:opacity-50"
        >
          {{ forgotLoading ? 'Sending...' : 'Send OTP' }}
        </button>

        <button @click="closeForgotModal" class="w-full border-2 border-transparent text-[#ef3f23] hover:text-red-700 py-3 text-[9px] uppercase tracking-widest font-bold transition-colors">
          Cancel
        </button>
      </template>

      <!-- Step 2: OTP + New Password -->
      <template v-if="forgotStep === 'otp'">
        <p class="text-sm font-bold mb-6 text-gray-700 leading-tight">
          Enter the 6-digit code and your new password.
        </p>

        <div class="flex gap-2 mb-6">
          <input
            v-for="(digit, index) in forgotOtp"
            :key="'forgot-'+index"
            ref="forgotOtpInputs"
            v-model="forgotOtp[index]"
            @input="handleForgotOtpInput(index, $event)"
            @keydown="handleForgotOtpKeydown(index, $event)"
            type="text"
            maxlength="1"
            class="w-10 h-14 sm:w-12 text-center text-2xl font-black bg-white border-2 border-[#1a1a1a] focus:outline-none focus:border-[#ef3f23] transition-colors"
          />
        </div>

        <input 
            v-model="forgotPassword" 
            type="password" 
            placeholder="NEW PASSWORD" 
            class="w-full bg-transparent border-b-2 border-[#1a1a1a] py-3 text-brutal-ink font-medium tracking-widest text-[12px] placeholder-gray-500 focus:outline-none focus:border-[#ef3f23] transition-colors mb-6 text-center"
            :disabled="forgotLoading"
        />

        <p v-if="forgotError" class="text-[10px] uppercase font-bold text-[#ef3f23] mb-4">{{ forgotError }}</p>

        <button 
          @click="verifyForgotOtp" 
          :disabled="forgotLoading"
          class="w-full bg-[#1a1a1a] text-white py-4 text-[11px] uppercase tracking-[0.4em] font-black hover:bg-[#ef3f23] transition-all transform active:scale-95 border-b-4 border-r-4 border-gray-600 mb-4 disabled:opacity-50"
        >
          {{ forgotLoading ? 'Resetting...' : 'Reset Password' }}
        </button>

        <div class="flex w-full justify-between gap-4">
          <button 
          @click="resendForgotOtp" 
          :disabled="forgotResendTimer > 0"
          class="flex-1 border-2 border-[#1a1a1a] py-3 text-[9px] uppercase tracking-widest font-bold transition-colors"
          :class="forgotResendTimer > 0 
          ? 'opacity-50 cursor-not-allowed' 
          : 'hover:bg-[#1a1a1a] hover:text-white'"
          >
            {{ forgotResendTimer > 0 ? `Resend in ${forgotResendTimer}s` : 'Resend OTP' }}
          </button>
          <button @click="closeForgotModal" class="flex-1 border-2 border-transparent text-[#ef3f23] hover:text-red-700 py-3 text-[9px] uppercase tracking-widest font-bold transition-colors">
            Cancel
          </button>
        </div>
      </template>

    </div>
  </div>
</transition>
</div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from "vue"
import { useRouter } from "vue-router"
import api from "../services/api"
import CaptchaBox from "../components/CaptchaBox.vue"

const router = useRouter()
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

// Form State
const email = ref("")
const password = ref("")
const errorMessage = ref("")
const isLoading = ref(false)

// Flow State
const isOtpFlow = ref(false)

// Captcha
const captchaVerified = ref(false)
const captchaRef = ref(null)

// OTP Modal State
const showOtpModal = ref(false)
const otp = ref(['', '', '', '', '', ''])
const otpInputs = ref([])
const otpError = ref("")
const otpLoading = ref(false)

//  RESEND TIMER STATE
const resendCooldown = ref(30)
const resendTimer = ref(0)
let resendInterval = null

// Forgot Password Modal State
const showForgotModal = ref(false)
const forgotStep = ref("email")
const forgotEmail = ref("")
const forgotOtp = ref(['', '', '', '', '', ''])
const forgotOtpInputs = ref([])
const forgotPassword = ref("")
const forgotError = ref("")
const forgotLoading = ref(false)

// FORGOT RESEND TIMER STATE
const forgotResendTimer = ref(0)
let forgotResendInterval = null


onMounted(() => {
  captchaRef.value?.generateCaptcha?.()
})

// ----------------------
// RESEND TIMER FUNCTIONS
// ----------------------
const startResendTimer = () => {
  resendTimer.value = resendCooldown.value

  clearInterval(resendInterval)

  resendInterval = setInterval(() => {
    if (resendTimer.value > 0) {
      resendTimer.value--
    } else {
      clearInterval(resendInterval)
    }
  }, 1000)
}

const startForgotResendTimer = () => {
  forgotResendTimer.value = resendCooldown.value

  clearInterval(forgotResendInterval)

  forgotResendInterval = setInterval(() => {
    if (forgotResendTimer.value > 0) {
      forgotResendTimer.value--
    } else {
      clearInterval(forgotResendInterval)
    }
  }, 1000)
}

// ----------------------
// MAIN FLOW
// ----------------------

const primaryButtonText = computed(() => {
  if (isLoading.value) return "Processing..."
  if (!captchaVerified.value) return "Verification Required"
  if (!isOtpFlow.value) return "Access Dashboard"
  return "Send OTP"
})

const toggleOtpFlow = () => {
  isOtpFlow.value = !isOtpFlow.value
  errorMessage.value = ""
  closeOtpModal()
}

const validateForm = () => {
  errorMessage.value = ""

  if (!email.value) {
    errorMessage.value = "Email is required."
    return false
  }

  if (!isOtpFlow.value && !password.value) {
    errorMessage.value = "Password is required."
    return false
  }

  if (!captchaVerified.value) {
    errorMessage.value = "Please complete the security directive."
    return false
  }

  return true
}

// ----------------------
// AUTH
// ----------------------

const handleAuthSuccess = (data) => {
  localStorage.setItem("access_token", data.access)
  localStorage.setItem("org_role", data.org_role || "")
  localStorage.setItem("org_slug", data.org_slug || "")

  localStorage.setItem(
    "username",
    data.display_name || data.email || "User"
  )
  localStorage.setItem("email", data.email || "")

  router.push("/org-home")
}

const login = async () => {
  isLoading.value = true
  try {
    const res = await api.post("login/", {
      email: email.value,   
      password: password.value
    })
    handleAuthSuccess(res.data)
  } catch (e) {
    errorMessage.value = "Invalid email or password."
  } finally {
    isLoading.value = false
  }
}

// ----------------------
// OTP LOGIN FLOW
// ----------------------

const sendOtp = async () => {
  isLoading.value = true
  errorMessage.value = ""
  otpError.value = ""

  try {
    await api.post("accounts/send-otp/", { email: email.value, mode:"login" })
    
    showOtpModal.value = true
    otp.value = ['', '', '', '', '', '']

    // START TIMER HERE
    startResendTimer()

    nextTick(() => {
      otpInputs.value[0]?.focus()
    })

  } catch {
    errorMessage.value = "Could not send OTP."
  } finally {
    isLoading.value = false
  }
}

const resendOtp = async () => {
  otpError.value = ""
  try {
    await api.post("accounts/send-otp/", { email: email.value ,mode:"login"})
    
    //  RESTART TIMER
    startResendTimer()

  } catch {
    otpError.value = "Failed to resend OTP."
  }
}

const handleOtpInput = (index, event) => {
  const value = event.target.value
  if (!/^\d*$/.test(value)) {
    otp.value[index] = ''
    return
  }
  if (value && index < 5) {
    otpInputs.value[index + 1]?.focus()
  }
}

const handleOtpKeydown = (index, event) => {
  if (event.key === 'Backspace' && !otp.value[index] && index > 0) {
    otpInputs.value[index - 1]?.focus()
  }
}

const closeOtpModal = () => {
  showOtpModal.value = false
  otp.value = ['', '', '', '', '', '']
  otpError.value = ""
}

const verifyOtp = async () => {
  const otpString = otp.value.join('')
  if (otpString.length !== 6) {
    otpError.value = "Please enter all 6 digits."
    return
  }

  otpLoading.value = true

  try {
    const res = await api.post("accounts/verify-otp/", {
      email: email.value,
      otp: otpString
    })
    closeOtpModal()
    handleAuthSuccess(res.data)
  } catch {
    otpError.value = "Invalid OTP"
  } finally {
    otpLoading.value = false
  }
}

const handleMainAction = () => {
  if (!validateForm()) return
  isOtpFlow.value ? sendOtp() : login()
}

const isValidPassword = (password) => {
  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/
  return passwordRegex.test(password)
}

const openForgotModal = () => {
  showForgotModal.value = true
}

const sendForgotOtp = async () => {
  if (!forgotEmail.value) {
    forgotError.value = "Please enter your email."
    return
  }

  forgotLoading.value = true
  forgotError.value = ""

  try {
    await api.post("accounts/send-otp/", {
      email: forgotEmail.value,
      mode: "forgot"
    })

    forgotStep.value = "otp"
    forgotOtp.value = ['', '', '', '', '', '']

    startForgotResendTimer()

    nextTick(() => {
      if (forgotOtpInputs.value && forgotOtpInputs.value.length > 0) {
        forgotOtpInputs.value[0]?.focus()
      }
    })

  } catch (error) {
    if (error.response && error.response.data) {
      const msg = (error.response.data.error || error.response.data.detail || Object.values(error.response.data).flat()[0] || "").toLowerCase()
      if (msg.includes("not registered") || msg.includes("no active account") || msg.includes("not found")) {
        forgotError.value = "Account not found."
      } else {
        forgotError.value = "Could not send OTP. Try again."
      }
    } else {
      forgotError.value = "Network error. Try again."
    }
  } finally {
    forgotLoading.value = false
  }
}

const resendForgotOtp = async () => {
  forgotError.value = ""
  try {
    await api.post("accounts/send-otp/", { 
        email: forgotEmail.value,
        mode: "forgot"
    })
    
    startForgotResendTimer()

  } catch {
    forgotError.value = "Failed to resend OTP."
  }
}

const handleForgotOtpInput = (index, event) => {
  const value = event.target.value
  
  if (!/^\d*$/.test(value)) {
    forgotOtp.value[index] = ''
    return
  }

  if (value && index < 5 && forgotOtpInputs.value[index + 1]) {
    forgotOtpInputs.value[index + 1]?.focus()
  }
}

const handleForgotOtpKeydown = (index, event) => {
  if (event.key === 'Backspace' && !forgotOtp.value[index] && index > 0 && forgotOtpInputs.value[index - 1]) {
    forgotOtpInputs.value[index - 1]?.focus()
  }
}

const verifyForgotOtp = async () => {
  const otpString = forgotOtp.value.join('')
  
  if (otpString.length !== 6) {
    forgotError.value = "Please enter all 6 digits."
    return
  }
  
  if (!forgotPassword.value) {
    forgotError.value = "New password is required."
    return
  }

  if (!isValidPassword(forgotPassword.value)) {
    forgotError.value = "Password must be at least 8 chars, with 1 uppercase, 1 lowercase, 1 number, and 1 special character."
    return
  }

  forgotLoading.value = true
  forgotError.value = ""

  try {
    await api.post("accounts/verify-otp-forgot/", {
      email: forgotEmail.value,
      otp: otpString,
      password: forgotPassword.value
    })

    alert("Password reset successfully. Please log in with your new password.")
    closeForgotModal()
    router.push("/login")

  } catch (error) {
    if (error.response && error.response.data) {
       const errorData = error.response.data
       const msg = errorData.detail || errorData.error || Object.values(errorData).flat()[0] || "Failed to reset password."
       forgotError.value = msg
    } else {
       forgotError.value = "Verification failed. Please check your connection."
    }
  } finally {
    forgotLoading.value = false
  }
}

const closeForgotModal = () => {
  showForgotModal.value = false
  forgotStep.value = "email"
  forgotEmail.value = ""
  forgotOtp.value = ['', '', '', '', '', '']
  forgotPassword.value = ""
  forgotError.value = ""
}

// ----------------------
// GOOGLE LOGIN
// ----------------------

const triggerGoogleLogin = () => {
  window.location.href =
    "https://accounts.google.com/o/oauth2/v2/auth?" +
    new URLSearchParams({
      client_id: GOOGLE_CLIENT_ID,
      redirect_uri: window.location.origin + "/auth/google",
      response_type: "id_token",
      scope: "openid email profile",
      nonce: "random_nonce_123456"
    })
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.captcha-theme-wrapper :deep(.bg-white) {
    background-color: transparent !important;
}
.captcha-theme-wrapper :deep(input) {
    background-color: rgba(255, 255, 255, 0.4) !important;
    border-color: #ccc !important;
}
</style>