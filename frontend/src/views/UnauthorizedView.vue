<template>
  <div class="flex items-center justify-center h-screen bg-[#0a0a0a] text-[#f5f5f5] font-sans p-6">
    <div class="max-w-md w-full bg-[#f5f5f5] text-[#1a1a1a] border-4 border-[#1a1a1a] p-10 flex flex-col items-center text-center shadow-[12px_12px_0px_0px_rgba(239,63,35,1)]">
      
      <h1 class="text-7xl font-black tracking-tighter text-[#ef3f23] mb-2 italic">404</h1>
      <h2 class="text-xl font-bold uppercase tracking-widest mb-6 border-b-2 border-[#1a1a1a] pb-4 w-full">Access Denied</h2>
      
      <p class="text-sm font-bold mb-8 text-gray-700 leading-tight">
        SESSION EXPIRED OR INVALID NAVIGATION DETECTED. SECURITY PROTOCOLS REQUIRE RE-AUTHENTICATION.
      </p>

      <div class="text-[10px] uppercase tracking-[0.3em] font-black text-gray-400 mb-2">
        Redirecting to login in
      </div>
      <div class="text-6xl font-black tracking-tighter mb-10 text-[#ef3f23]">
        {{ countdown }}
      </div>

      <button @click="goToLogin" class="w-full bg-[#1a1a1a] text-white py-5 text-[11px] uppercase tracking-[0.4em] font-black hover:bg-[#ef3f23] transition-all transform active:scale-95 border-b-4 border-r-4 border-gray-600">
        Relogin Now
      </button>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const countdown = ref(3);
let timer = null;

const goToLogin = () => {
  if (timer) clearInterval(timer);
  router.push('/login');
};

onMounted(() => {
  timer = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      goToLogin();
    }
  }, 1000);
});

onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>