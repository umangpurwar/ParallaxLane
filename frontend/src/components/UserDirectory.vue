<template>
  <div class="max-w-4xl mx-auto pb-10">
    <div class="mb-8">
      <h2 class="text-3xl font-medium tracking-tighter text-brutal-ink">Organisation Members</h2>
      <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500 mt-1">
        Manage users and send invites
      </p>
    </div>

    <div class="bg-white border border-brutal-border p-6 mb-8">
      <h3 class="text-[10px] uppercase tracking-super-wide font-bold text-brutal-red mb-4">Invite Member</h3>
      <form @submit.prevent="sendInvite" class="flex flex-col md:flex-row gap-4">
        <input
          v-model="inviteEmail"
          type="email"
          required
          placeholder="Email address"
          class="flex-1 border-b border-brutal-border py-2 text-sm focus:outline-none focus:border-brutal-red bg-transparent"
        />
        <select
          v-model="inviteRole"
          class="border-2 border-brutal-ink px-3 py-2 text-xs font-bold uppercase bg-white"
        >
          <option value="candidate">Candidate</option>
          <option value="invigilator">Invigilator</option>
          <option value="admin">Admin</option>
        </select>
        <button
          type="submit"
          :disabled="inviteLoading"
          class="px-6 py-2 bg-brutal-ink text-white text-[10px] uppercase tracking-widest font-bold hover:bg-brutal-red transition-colors disabled:opacity-50"
        >
          {{ inviteLoading ? 'Sending...' : 'Invite' }}
        </button>
      </form>
      <p v-if="inviteMessage" class="text-[10px] uppercase font-bold mt-3" :class="inviteError ? 'text-brutal-red' : 'text-emerald-600'">
        {{ inviteMessage }}
      </p>
      <p v-if="inviteToken" class="text-xs mt-2 text-gray-600 break-all">
        Share this invite code: <span class="font-mono font-bold">{{ inviteToken }}</span>
      </p>
    </div>

    <div v-if="loading" class="text-sm text-gray-500">Loading members...</div>

    <table v-else class="w-full text-sm text-left border border-brutal-border bg-white">
      <thead class="bg-gray-100">
        <tr>
          <th class="p-3 border text-[9px] uppercase tracking-widest font-bold">Username</th>
          <th class="p-3 border text-[9px] uppercase tracking-widest font-bold">Email</th>
          <th class="p-3 border text-[9px] uppercase tracking-widest font-bold">Role</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="member in members" :key="member.email">
          <td class="p-3 border">{{ member.username }}</td>
          <td class="p-3 border">{{ member.email }}</td>
          <td class="p-3 border uppercase text-xs font-bold">{{ member.role }}</td>
        </tr>
        <tr v-if="members.length === 0">
          <td colspan="3" class="p-6 text-center text-gray-400 italic">No members found.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/services/api'

const members = ref([])
const loading = ref(false)
const inviteEmail = ref('')
const inviteRole = ref('candidate')
const inviteLoading = ref(false)
const inviteMessage = ref('')
const inviteError = ref(false)
const inviteToken = ref('')

const orgSlug = () => localStorage.getItem('org_slug')

const fetchMembers = async () => {
  const slug = orgSlug()
  if (!slug) return

  loading.value = true
  try {
    const res = await api.get(`organisations/${slug}/members/`)
    members.value = res.data || []
  } catch (e) {
    console.error('Failed to load members', e)
  } finally {
    loading.value = false
  }
}

const sendInvite = async () => {
  const slug = orgSlug()
  if (!slug) return

  inviteLoading.value = true
  inviteMessage.value = ''
  inviteError.value = false
  inviteToken.value = ''

  try {
    const res = await api.post(`organisations/${slug}/invite/`, {
      email: inviteEmail.value.trim().toLowerCase(),
      role: inviteRole.value,
    })

    if (res.data.invite_token) {
      inviteToken.value = res.data.invite_token
      inviteMessage.value = 'Invite created. Share the code below with the user.'
    } else {
      inviteMessage.value = res.data.status || 'User added successfully.'
    }

    inviteEmail.value = ''
    await fetchMembers()
  } catch (e) {
    inviteError.value = true
    inviteMessage.value = e.response?.data?.error || 'Failed to send invite.'
  } finally {
    inviteLoading.value = false
  }
}

onMounted(fetchMembers)
</script>
