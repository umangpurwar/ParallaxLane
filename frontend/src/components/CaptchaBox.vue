<template>
  <div class="bg-[#e8e4d9] p-4 flex flex-col gap-3">
    
    <div class="flex justify-between items-center">
      <span class="text-[9px] uppercase tracking-widest font-bold text-gray-500">
        Captcha
      </span>
      <button @click="generateCaptcha" class="text-[10px] text-brutal-ink hover:text-brutal-red font-bold transition-colors">
        ↻ REFRESH
      </button>
    </div>

    <!-- captcha display -->
    <div class="bg-brutal-ink text-brutal-paper py-3 px-4 text-center tracking-[0.3em] font-black text-lg select-none">
      {{ captchaTarget }}
    </div>

    <!-- input and check  -->
    <div class="relative">
      <input 
        v-model="captchaInput"
        @input="verifyCaptcha"
        type="text"
        placeholder="enter captcha here"
        class="w-full hover:bg-[#e8e4d9] border-2 border-brutal-border py-2 px-3 text-center text-brutal-ink font-bold tracking-widest text-[12px] placeholder-gray-400 focus:outline-none focus:border-brutal-ink transition-colors pr-10"
      />

      <!-- checkmark -->
      <span 
        v-if="captchaVerified"
        class="absolute right-3 top-1/2 -translate-y-1/2 text-emerald-600 font-bold"
      >
        ✔
      </span>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from "vue"

const emit = defineEmits(["verified"])

const captchaTarget = ref("")
const captchaInput = ref("")
const captchaVerified = ref(false)

// mixed captcha
const generateCaptcha = () => {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz0123456789"
  let result = ""
  for (let i = 0; i < 5; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }

  captchaTarget.value = result
  captchaInput.value = ""
  captchaVerified.value = false
}

// case sensitive check 
const verifyCaptcha = () => {
  captchaVerified.value = captchaInput.value === captchaTarget.value
}

// emit state to parent 
watch(captchaVerified, (val) => {
  emit("verified", val)
})

onMounted(() => {
  generateCaptcha()
})

defineExpose({
  generateCaptcha
})
</script>