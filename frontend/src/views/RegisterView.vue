<template>
  <div class="relative w-full h-screen overflow-hidden bg-brutal-dark font-sans">
    <div class="fixed inset-0 z-0 bg-brutal-maroon overflow-hidden">
        <div class="absolute top-[-10%] left-[0%] w-[80%] h-[80%] bg-brutal-glow1 rounded-full mix-blend-screen filter blur-[140px] opacity-70 animate-pulse"></div>
        <div class="absolute bottom-[-10%] right-[-10%] w-[70%] h-[70%] bg-brutal-glow2 rounded-full mix-blend-screen filter blur-[150px] opacity-80"></div>
    </div>

    <transition name="reveal" appear>
      <div class="relative z-10 w-[92vw] max-w-[1600px] h-[90vh] mx-auto mt-[5vh] bg-brutal-paper shadow-2xl flex flex-col overflow-hidden">
        
        <div class="absolute inset-0 pointer-events-none z-0">
            <div class="grid-line-v left-[25%] hidden md:block"></div>
            <div class="grid-line-v left-[50%]"></div>
            <div class="grid-line-v left-[75%] hidden lg:block"></div>
            <div class="grid-line-h top-[20%]"></div>
        </div>

        <header class="absolute top-0 left-0 w-full h-[20%] flex z-20">
            <div class="w-full md:w-[25%] h-full flex items-center justify-center md:justify-start md:px-8 font-bold tracking-super-wide text-[13px] text-black bg-brutal-paper md:bg-transparent">
                PARALLAXLANE
            </div>
            <div class="hidden md:flex w-[75%] h-full items-center px-8 justify-end">
                <router-link to="/" class="text-[9px] uppercase tracking-normal font-semibold text-gray-700 hover:text-brutal-red transition-colors pointer-events-auto">
                    RETURN HOME
                </router-link>
            </div>
        </header>

        <main class="absolute top-[20%] bottom-0 left-0 w-full flex flex-col md:flex-row z-10">
            
            <!-- LEFT COLUMN (Branding) -->
            <div class="hidden md:flex w-[50%] h-full flex-col justify-center px-12 md:px-16 lg:px-24 pointer-events-auto bg-brutal-paper/80 backdrop-blur-sm md:bg-transparent md:backdrop-blur-none">
                <p class="text-[9px] uppercase tracking-wide-ish font-bold text-brutal-red mb-6">
                    Registration
                </p>
                <h1 class="text-[3rem] lg:text-[4rem] font-medium tracking-tighter leading-none text-brutal-ink mb-8">
                    Secure.<br>Fair.<br>Unbiased.
                </h1>
                <p class="text-[1.1rem] lg:text-[1.25rem] font-medium tracking-tight leading-[1.4] text-[#333] max-w-md">
                    Welcome to ParallaxLane. We transform exams into trusted evaluations where <span class="text-brutal-red font-semibold">integrity</span> is built in. Create your profile to let your merit speak for itself.
                </p>
            </div>
            
            <!-- RIGHT HALF -->
            <div class="w-full md:w-[50%] h-full flex flex-col justify-center px-8 md:px-12 lg:px-16 pointer-events-auto bg-brutal-paper">

                
                <div class="w-full flex flex-col">
                    
                    <!-- TOP SECTION: Two-Column Form Layout -->
                    <div class="flex flex-col lg:flex-row w-full gap-8 lg:gap-12 mb-8">
                        
                        <!-- Left Column: Inputs -->
                        <div class="w-full lg:w-[50%] flex flex-col gap-3">
                            <div class="relative">
                                <input 
                                    v-model="name" 
                                    type="text" 
                                    placeholder="NAME" 
                                    class="w-full bg-transparent border-b-2 border-brutal-border py-3 text-brutal-ink font-medium tracking-normal text-[12px] placeholder-gray-500 focus:outline-none focus:border-brutal-red transition-colors"
                                />
                            </div>
                            
                            <div class="relative">
                                <input 
                                    v-model="email" 
                                    type="email" 
                                    placeholder="EMAIL" 
                                    class="w-full bg-transparent border-b-2 border-brutal-border py-3 text-brutal-ink font-medium tracking-normal text-[12px] placeholder-gray-500 focus:outline-none focus:border-brutal-red transition-colors"
                                />
                            </div>
                            
                            <div class="relative">
                                <input 
                                    v-model="password" 
                                    type="password" 
                                    placeholder="PASSWORD" 
                                    class="w-full bg-transparent border-b-2 border-brutal-border py-3 text-brutal-ink font-medium tracking-normal text-[12px] placeholder-gray-500 focus:outline-none focus:border-brutal-red transition-colors"
                                />
                            </div>

                            <div class="relative">
                                <input 
                                    v-model="confirmPassword" 
                                    type="password" 
                                    placeholder="RE-ENTER PASSWORD" 
                                    class="w-full bg-transparent border-b-2 border-brutal-border py-3 text-brutal-ink font-medium tracking-normal text-[12px] placeholder-gray-500 focus:outline-none focus:border-brutal-red transition-colors"
                                />
                            </div>
                        </div>

                        <!-- Right Column: Captcha -->
                        <div class="w-full lg:w-[50%] flex flex-col justify-center border-t-2 border-brutal-border pt-8 lg:border-t-0 lg:pt-0">
                            <CaptchaBox @verified="captchaVerified = $event" />
                        </div>

                    </div>

                    <!-- BOTTOM SECTION: Actions -->
                    <div class="w-full flex flex-col items-center gap-4 mt-2">
                        
                        <p v-if="errorMessage" class="text-[10px] uppercase tracking-normal font-bold text-brutal-red leading-tight text-center w-full">
                            {{ errorMessage }}
                        </p>
                        
                        <button 
                            @click="register" 
                            :disabled="!captchaVerified"
                            class="w-full py-4 text-[10px] uppercase tracking-super-wide font-bold transition-all duration-300"
                            :class="captchaVerified ? 'bg-brutal-ink hover:bg-brutal-red text-brutal-paper cursor-pointer' : 'bg-gray-300 text-gray-500 cursor-not-allowed'"
                        >
                            {{ captchaVerified ? 'Create Profile' : 'Register' }}
                        </button>
                        
                        
                        <button 
                        @click="triggerGoogleLogin"
                        type="button"
                        class="w-full py-4 text-[10px] uppercase tracking-super-wide font-bold transition-all duration-300 border-2 border-brutal-ink text-brutal-ink hover:bg-brutal-ink hover:text-brutal-paper flex items-center justify-center gap-3">
                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12.24 10.285V14.4h6.806c-.275 1.765-2.056 5.174-6.806 5.174-4.095 0-7.439-3.389-7.439-7.574s3.345-7.574 7.439-7.574c2.33 0 3.891.989 4.785 1.849l3.254-3.138C18.189 1.186 15.479 0 12.24 0c-6.635 0-12 5.365-12 12s5.365 12 12 12c6.926 0 11.52-4.869 11.52-11.726 0-.788-.085-1.39-.189-1.989H12.24z"/></svg>
                            Continue with Google
                        </button>

                        <button 
                            @click="$router.push('/login')" 
                            class="text-[9px] uppercase tracking-normal font-semibold text-gray-600 hover:text-brutal-red transition-colors text-center mt-2"
                        >
                            Already have an account? Log In
                        </button>
                        
                    </div>

                </div>
            </div>
            
        </main>

        <div class="absolute bottom-6 right-8 z-30 pointer-events-none text-[9px] uppercase tracking-super-wide font-bold text-gray-500">
            &copy; UMNG & KUSIK
        </div>
      </div>
    </transition>

    <!-- NEW OTP MODAL OVERLAY -->
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
              :key="index"
              ref="otpInputs"
              v-model="otp[index]"
              @input="handleOtpInput(index, $event)"
              @keydown="handleOtpKeydown(index, $event)"
              type="text"
              maxlength="1"
              class="w-10 h-14 sm:w-12 text-center text-2xl font-black bg-transparent border-2 border-[#1a1a1a] focus:outline-none focus:border-[#ef3f23] focus:bg-white transition-colors"
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
            <button @click="closeOtpModal" class="flex-1 border-2 border-transparent text-gray-500 hover:text-[#ef3f23] py-3 text-[9px] uppercase tracking-widest font-bold transition-colors">
              Cancel
            </button>
          </div>

        </div>
      </div>
    </transition>

  </div>
</template>

```vue
<script setup>
import { ref, onMounted, nextTick } from "vue"
import { useRouter } from "vue-router"
import api from "../services/api"
import CaptchaBox from "../components/CaptchaBox.vue"

const router = useRouter()

const name = ref("")
const email = ref("")
const password = ref("")
const confirmPassword = ref("")
const errorMessage = ref("")
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID

// Captcha State
const captchaVerified = ref(false)
const captchaRef = ref(null)

// OTP STATE
const showOtpModal = ref(false)
const otp = ref(['', '', '', '', '', ''])
const otpInputs = ref([])
const otpLoading = ref(false)
const otpError = ref("")

onMounted(() => {
  captchaRef.value?.generateCaptcha?.()
})

const validateForm = () => {
  errorMessage.value = ""

  if (!name.value || !email.value || !password.value || !confirmPassword.value) {
    errorMessage.value = "All fields are required."
    return false
  }

  const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/
  
  if (!passwordRegex.test(password.value)) {
    errorMessage.value = "Password must be at least 8 chars, with 1 uppercase, 1 lowercase, 1 number, and 1 special character."
    return false
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = "Passwords do not match."
    return false
  }

  if (!captchaVerified.value) {
    errorMessage.value = "Please complete the security directive."
    return false
  }

  return true
}

//  SEND OTP
const register = async () => {
  if (!validateForm()) return

  try {
    await api.post("accounts/send-otp/", {
      email: email.value.trim().toLowerCase(),   // FIX: normalize email
      mode: "register"
    })
    
    showOtpModal.value = true
    startResendTimer()
    otp.value = ['', '', '', '', '', '']         // FIX: reset OTP

    nextTick(() => {
      otpInputs.value[0]?.focus()
    })

  } catch (error) {
    if (error.response && error.response.data) {
      const errors = Object.values(error.response.data).flat()
      errorMessage.value = errors[0] || "Failed to send OTP."
    } else {
      errorMessage.value = "Failed to send OTP."
    }
  }
}

// OTP INPUT HANDLING
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

// VERIFY OTP + REGISTER
const verifyOtp = async () => {
  const otpString = otp.value.join('')

  if (otpString.length !== 6) {
    otpError.value = "Please enter all 6 digits."
    return
  }

  otpLoading.value = true
  otpError.value = ""

  try {
    await api.post("accounts/verify-otp-register/", {
      email: email.value.trim().toLowerCase(),  // FIX: normalize email
      otp: otpString,
      name: name.value,
      password: password.value
    })

    closeOtpModal()
    alert("Registered successfully. Please log in.")
    router.push("/login")

  } catch (error) {
    if (error.response && error.response.data) {
      const errors = Object.values(error.response.data).flat()
      otpError.value = errors[0] || "Invalid OTP."
    } else {
      otpError.value = "Verification failed."
    }
  } finally {
    otpLoading.value = false
  }
}

const resendCooldown = ref(30)   // 30 seconds
const resendTimer = ref(0)
let resendInterval = null

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

// RESEND OTP
const resendOtp = async () => {
  otpError.value = ""
  try {
    await api.post("accounts/send-otp/", {
      email: email.value.trim().toLowerCase(),  // FIX
      mode: "register"
    })
    alert("OTP has been resent.")
    startResendTimer()
  } catch {
    otpError.value = "Failed to resend OTP."
  }
}

// CLOSE MODAL
const closeOtpModal = () => {
  showOtpModal.value = false
  otp.value = ['', '', '', '', '', '']
  otpError.value = ""
}

// GOOGLE LOGIN (same as login view)
const triggerGoogleLogin = () => {
  console.log("REGISTER GOOGLE CLICKED")   // add this
  window.location.href =
    "https://accounts.google.com/o/oauth2/v2/auth?" +
    new URLSearchParams({
      client_id:GOOGLE_CLIENT_ID,
      redirect_uri: window.location.origin + "/auth/google",
      response_type: "id_token",
      scope: "openid email profile",
      nonce: "random_nonce_123456"
    })
}
</script>
```

```
