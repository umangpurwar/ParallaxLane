<template>
  <form class="space-y-4" novalidate @submit.prevent="$emit('submit')">
    <div v-if="showName">
      <label class="label" for="org-name">Organisation name</label>
      <input id="org-name" v-model="model.name" class="input" maxlength="60" />
      <p class="help">Letters, numbers, spaces and &amp; ( ) , ' only. It cannot be changed after approval.</p>
    </div>
    <div>
      <label class="label" for="org-description">About the organisation</label>
      <textarea id="org-description" v-model="model.description" rows="4" class="textarea" maxlength="2000"
        placeholder="Who you are, how many candidates you expect and how you will use exams"></textarea>
    </div>
    <div class="grid gap-4 sm:grid-cols-2">
      <div>
        <label class="label" for="org-phone">Contact phone</label>
        <input id="org-phone" v-model="model.contact_phone" class="input" maxlength="30" />
      </div>
      <div>
        <label class="label" for="org-website">Website</label>
        <input id="org-website" v-model="model.website" class="input" placeholder="https://" />
      </div>
    </div>
    <p v-if="error" class="field-error" role="alert">{{ error }}</p>
    <div class="flex justify-end"><button type="submit" class="btn-primary" :disabled="busy">{{ busy ? 'Saving…' : submitLabel }}</button></div>
  </form>
</template>

<script setup>
defineProps({ showName: { type: Boolean, default: true }, error: String, busy: Boolean, submitLabel: String })
defineEmits(['submit'])
const model = defineModel({ type: Object, required: true })
</script>
