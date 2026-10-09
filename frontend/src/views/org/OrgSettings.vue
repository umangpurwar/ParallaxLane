<template>
  <PageHeader title="Settings" />
  <StateBlock :loading="loading" :error="error" @retry="load">
    <div class="space-y-6">
      <section class="panel p-5">
        <h2 class="text-sm font-semibold">Organisation details</h2>
        <p class="mb-4 mt-1 text-sm text-neutral-500">Shown to the platform administrators. The name <strong>{{ profile.name }}</strong> is fixed after approval.</p>
        <OrgDetailsForm v-model="profile" :show-name="false" :error="profileError" :busy="savingProfile" submit-label="Save details" @submit="saveProfile" />
      </section>

      <section class="panel p-5">
        <h2 class="text-sm font-semibold">Join code</h2>
        <p class="mt-1 text-sm text-neutral-500">Candidates can join by typing this code in the app. Anyone with the code can join while it is enabled, up to your candidate limit.</p>
        <div class="mt-4 flex flex-wrap items-center gap-4">
          <span class="rounded-md border border-neutral-300 px-4 py-2 font-mono text-xl tracking-[0.3em]">{{ join.join_code }}</span>
          <StatusBadge :status="join.join_code_enabled ? 'active' : 'disabled'" :label="join.join_code_enabled ? 'Enabled' : 'Disabled'" />
        </div>
        <div class="mt-4 grid gap-4 sm:grid-cols-2">
          <div><label class="label" for="valid-from">Valid from (optional)</label><input id="valid-from" v-model="validFrom" type="datetime-local" class="input" /></div>
          <div><label class="label" for="valid-until">Valid until (optional)</label><input id="valid-until" v-model="validUntil" type="datetime-local" class="input" /></div>
        </div>
        <p v-if="joinError" class="field-error" role="alert">{{ joinError }}</p>
        <div class="mt-4 flex flex-wrap gap-2">
          <button class="btn-primary" :disabled="savingJoin" @click="saveJoin({ join_code_enabled: !join.join_code_enabled })">{{ join.join_code_enabled ? 'Disable code' : 'Enable code' }}</button>
          <button class="btn-secondary" :disabled="savingJoin" @click="saveJoin({})">Save dates</button>
          <button class="btn-secondary" :disabled="savingJoin" @click="saveJoin({ regenerate_code: true })">Generate a new code</button>
        </div>
      </section>
    </div>
  </StateBlock>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import OrgDetailsForm from '@/components/OrgDetailsForm.vue'
import { org } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { fromLocalInput, toLocalInput } from '@/format'

const slug = useRoute().params.slug
const loading = ref(true)
const error = ref(null)
const profile = ref(null)
const profileError = ref('')
const savingProfile = ref(false)
const join = ref(null)
const validFrom = ref('')
const validUntil = ref('')
const joinError = ref('')
const savingJoin = ref(false)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [overview, code] = await Promise.all([org.overview(slug), org.joinCode(slug)])
    const o = overview.organisation
    profile.value = { name: o.name, description: o.description, contact_phone: o.contact_phone, website: o.website }
    setJoin(code)
  } catch (e) {
    error.value = e
  } finally {
    loading.value = false
  }
}

function setJoin(code) {
  join.value = code
  validFrom.value = toLocalInput(code.join_code_valid_from)
  validUntil.value = toLocalInput(code.join_code_valid_until)
}

async function saveProfile() {
  savingProfile.value = true
  profileError.value = ''
  try {
    const { description, contact_phone, website } = profile.value
    await org.updateProfile(slug, { description, contact_phone, website })
    toast.success('Details saved')
  } catch (e) {
    profileError.value = e.message
  } finally {
    savingProfile.value = false
  }
}

async function saveJoin(extra) {
  savingJoin.value = true
  joinError.value = ''
  try {
    const body = { ...extra }
    if (validFrom.value) body.join_code_valid_from = fromLocalInput(validFrom.value)
    if (validUntil.value) body.join_code_valid_until = fromLocalInput(validUntil.value)
    setJoin(await org.updateJoinCode(slug, body))
    toast.success('Join code updated')
  } catch (e) {
    joinError.value = e.message
  } finally {
    savingJoin.value = false
  }
}

onMounted(load)
</script>
