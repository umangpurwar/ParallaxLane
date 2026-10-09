<template>
  <SimpleShell>
    <PageHeader title="Register your organisation" description="A platform administrator reviews every application. You can invite members and create exams once it is approved." />
    <div class="panel p-6">
      <OrgDetailsForm v-model="form" :error="error" :busy="busy" submit-label="Submit application" @submit="submit" />
    </div>
  </SimpleShell>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import SimpleShell from '@/components/SimpleShell.vue'
import PageHeader from '@/components/PageHeader.vue'
import OrgDetailsForm from '@/components/OrgDetailsForm.vue'
import { applications } from '@/api/endpoints'
import { session } from '@/stores/session'
import { toast } from '@/stores/toast'

const router = useRouter()
const form = reactive({ name: '', description: '', contact_phone: '', website: '' })
const error = ref('')
const busy = ref(false)

async function submit() {
  if (!form.name.trim() || !form.description.trim()) {
    error.value = 'Name and description are required.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await applications.submit({ ...form })
    await session.load(true)
    toast.success('Application submitted for review')
    router.replace({ name: 'application' })
  } catch (e) {
    error.value = e.message
    if (e.code === 'application_pending' || e.code === 'application_rejected') {
      await session.load(true)
      router.replace({ name: 'application' })
    }
  } finally {
    busy.value = false
  }
}
</script>
