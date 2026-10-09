<template>
  <Modal :open="open" :title="title" @close="close">
    <p class="text-sm text-neutral-600">{{ message }}</p>
    <div v-if="reasonLabel" class="mt-4">
      <label class="label" for="confirm-reason">{{ reasonLabel }}</label>
      <textarea id="confirm-reason" v-model="reason" rows="3" class="textarea" :placeholder="reasonRequired ? 'Required' : 'Optional'"></textarea>
    </div>
    <template #footer>
      <button class="btn-secondary" :disabled="busy" @click="close">Cancel</button>
      <button :class="danger ? 'btn-danger' : 'btn-primary'" :disabled="busy || (reasonRequired && !reason.trim())" @click="confirm">
        {{ busy ? 'Working…' : confirmLabel }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import Modal from './Modal.vue'

const props = defineProps({
  open: Boolean, title: String, message: String, confirmLabel: { type: String, default: 'Confirm' },
  danger: Boolean, reasonLabel: String, reasonRequired: Boolean, action: Function,
})
const emit = defineEmits(['close', 'done'])
const reason = ref('')
const busy = ref(false)
watch(() => props.open, (value) => { if (value) reason.value = '' })

function close() { if (!busy.value) emit('close') }

// Runs the supplied async action once; the button stays disabled until it settles.
async function confirm() {
  busy.value = true
  try {
    const result = await props.action?.(reason.value.trim())
    emit('done', result)
    emit('close')
  } catch {
    // The caller already showed the error; keep the dialog open to retry.
  } finally {
    busy.value = false
  }
}
</script>
