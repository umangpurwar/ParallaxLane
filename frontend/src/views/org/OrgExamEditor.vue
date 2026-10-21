<template>
  <PageHeader :title="isNew ? 'New exam' : 'Edit exam'" :back="{ name: 'org-exams', params: { slug } }" back-label="Exams" />
  <StateBlock :loading="loading" :error="loadError" @retry="load">
    <form class="space-y-6" novalidate @submit.prevent="save">
      <section class="panel space-y-4 p-5">
        <h2 class="text-sm font-semibold">Details</h2>
        <div>
          <label class="label" for="title">Title</label>
          <input id="title" v-model="exam.title" class="input" maxlength="200" />
        </div>
        <div>
          <label class="label" for="description">Instructions for candidates</label>
          <textarea id="description" v-model="exam.description" rows="3" class="textarea"></textarea>
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <div><label class="label" for="start">Opens</label><input id="start" v-model="startLocal" type="datetime-local" class="input" /></div>
          <div><label class="label" for="end">Closes</label><input id="end" v-model="endLocal" type="datetime-local" class="input" /></div>
          <div><label class="label" for="duration">Duration (minutes)</label><input id="duration" v-model.number="exam.duration" type="number" min="1" max="1440" class="input" /></div>
        </div>
        <div class="grid gap-4 sm:grid-cols-3">
          <div>
            <label class="label" for="violations">Warnings before ending</label>
            <input id="violations" v-model.number="exam.violation_limit" type="number" min="1" max="100" class="input" />
          </div>
          <label class="flex items-center gap-2 text-sm sm:mt-6"><input v-model="exam.auto_submit_on_violation" type="checkbox" class="h-4 w-4 accent-neutral-900" />End the exam at the limit</label>
          <label class="flex items-center gap-2 text-sm sm:mt-6"><input v-model="exam.is_published" type="checkbox" class="h-4 w-4 accent-neutral-900" />Published</label>
        </div>
        <label class="flex items-center gap-2 text-sm"><input v-model="exam.is_active" type="checkbox" class="h-4 w-4 accent-neutral-900" />Enabled: candidates can start it while it is open (published exams that are not enabled are listed but cannot be started)</label>
      </section>

      <section class="panel p-5">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold">Questions <span class="font-normal text-neutral-500">({{ exam.questions.length }}, {{ totalPoints }} points)</span></h2>
          <button v-if="!locked" type="button" class="btn-secondary h-8" @click="addQuestion"><Plus class="h-4 w-4" />Add question</button>
        </div>
        <p v-if="locked" class="mt-3 rounded-md border border-neutral-200 bg-neutral-50 p-3 text-sm">
          Candidates have already started this exam, so its questions are locked to keep results consistent. You can still change the details above.
        </p>
        <p v-else-if="!exam.questions.length" class="mt-4 text-sm text-neutral-500">Add at least one question.</p>

        <ol class="mt-4 space-y-4">
          <li v-for="(q, qi) in exam.questions" :key="q._key" class="rounded-md border border-neutral-200 p-4">
            <fieldset :disabled="locked" class="space-y-3">
              <div class="flex items-start justify-between gap-3">
                <span class="text-xs font-medium uppercase tracking-wide text-neutral-500">Question {{ qi + 1 }}</span>
                <div v-if="!locked" class="flex gap-1">
                  <button type="button" class="btn-ghost h-7 w-7 px-0" :disabled="qi === 0" aria-label="Move up" @click="move(qi, -1)"><ArrowUp class="h-4 w-4" /></button>
                  <button type="button" class="btn-ghost h-7 w-7 px-0" :disabled="qi === exam.questions.length - 1" aria-label="Move down" @click="move(qi, 1)"><ArrowDown class="h-4 w-4" /></button>
                  <button type="button" class="btn-ghost h-7 w-7 px-0" aria-label="Remove question" @click="exam.questions.splice(qi, 1)"><Trash2 class="h-4 w-4" /></button>
                </div>
              </div>
              <textarea v-model="q.text" rows="2" class="textarea" placeholder="Question text" :aria-label="`Question ${qi + 1} text`"></textarea>
              <div class="grid gap-3 sm:grid-cols-3">
                <select v-model="q.question_type" class="input" aria-label="Question type" @change="resetType(q)">
                  <option v-for="t in questionTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
                </select>
                <label class="flex items-center gap-2 text-sm">Points <input v-model.number="q.points" type="number" min="0" max="1000" class="input w-20" /></label>
                <label class="flex items-center gap-2 text-sm">Negative <input v-model.number="q.negative_points" type="number" min="0" max="1000" class="input w-20" /></label>
              </div>
              <div v-if="q.question_type === 'short_answer'">
                <input v-model="q.correct_text_answer" class="input" placeholder="Correct answer (compared ignoring case and spaces at the ends)" aria-label="Correct answer" />
              </div>
              <div v-else class="space-y-2">
                <div v-for="(o, oi) in q.options" :key="oi" class="flex items-center gap-2">
                  <input type="radio" :name="`correct-${q._key}`" :checked="o.is_correct" class="h-4 w-4 accent-neutral-900" :aria-label="`Mark option ${oi + 1} correct`" @change="setCorrect(q, oi)" />
                  <input v-model="o.text" class="input" :placeholder="`Option ${oi + 1}`" :readonly="q.question_type === 'true_false'" />
                  <button v-if="q.question_type === 'mcq' && q.options.length > 2" type="button" class="btn-ghost h-8 w-8 px-0" aria-label="Remove option" @click="q.options.splice(oi, 1)"><X class="h-4 w-4" /></button>
                </div>
                <button v-if="q.question_type === 'mcq' && q.options.length < 8" type="button" class="btn-ghost h-8" @click="q.options.push({ text: '', is_correct: false })"><Plus class="h-4 w-4" />Add option</button>
              </div>
              <input v-model="q.explanation" class="input" placeholder="Explanation shown to admins (optional)" aria-label="Explanation" />
            </fieldset>
          </li>
        </ol>
      </section>

      <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      <div class="flex justify-end gap-2">
        <RouterLink :to="{ name: 'org-exams', params: { slug } }" class="btn-secondary">Cancel</RouterLink>
        <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : isNew ? 'Create exam' : 'Save changes' }}</button>
      </div>
    </form>
  </StateBlock>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, ArrowUp, Plus, Trash2, X } from 'lucide-vue-next'
import PageHeader from '@/components/PageHeader.vue'
import StateBlock from '@/components/StateBlock.vue'
import { exams as examApi } from '@/api/endpoints'
import { toast } from '@/stores/toast'
import { fromLocalInput, toLocalInput } from '@/format'

const route = useRoute()
const router = useRouter()
const slug = route.params.slug
const examId = route.params.examId
const isNew = !examId
let keySeq = 0

const blankQuestion = () => ({
  _key: ++keySeq, text: '', question_type: 'mcq', points: 1, negative_points: 0, correct_text_answer: '', explanation: '',
  options: [{ text: '', is_correct: true }, { text: '', is_correct: false }, { text: '', is_correct: false }, { text: '', is_correct: false }],
})
const exam = ref({ title: '', description: '', duration: 30, violation_limit: 3, auto_submit_on_violation: true, is_published: false, is_active: false, questions: [blankQuestion()] })
const startLocal = ref('')
const endLocal = ref('')
const locked = ref(false)
const loading = ref(!isNew)
const loadError = ref(null)
const error = ref('')
const saving = ref(false)
// Question types this editor has form controls for.
const questionTypes = [
  { value: 'mcq', label: 'Multiple choice' },
  { value: 'true_false', label: 'True or false' },
  { value: 'short_answer', label: 'Short answer' },
]
const totalPoints = computed(() => exam.value.questions.reduce((sum, q) => sum + (Number(q.points) || 0), 0))

async function load() {
  loading.value = true
  loadError.value = null
  try {
    const data = await examApi.detail(examId)
    data.questions = data.questions.map((q) => ({ ...q, _key: ++keySeq, correct_text_answer: q.correct_text_answer || '', explanation: q.explanation || '' }))
    exam.value = data
    locked.value = data.has_attempts
    startLocal.value = toLocalInput(data.start_time)
    endLocal.value = toLocalInput(data.end_time)
  } catch (e) {
    loadError.value = e
  } finally {
    loading.value = false
  }
}

function addQuestion() { exam.value.questions.push(blankQuestion()) }
function move(i, d) { const qs = exam.value.questions; [qs[i], qs[i + d]] = [qs[i + d], qs[i]] }
function setCorrect(q, index) { q.options.forEach((o, i) => { o.is_correct = i === index }) }
function resetType(q) {
  if (q.question_type === 'true_false') q.options = [{ text: 'True', is_correct: true }, { text: 'False', is_correct: false }]
  else if (q.question_type === 'mcq' && q.options.length < 2) q.options = blankQuestion().options
}

// Client checks mirror the server's rules so most mistakes are caught before the request.
function validate() {
  const e = exam.value
  if (!e.title.trim()) return 'Give the exam a title.'
  if (!startLocal.value || !endLocal.value) return 'Set when the exam opens and closes.'
  if (new Date(endLocal.value) <= new Date(startLocal.value)) return 'The closing time must be after the opening time.'
  if (!(e.duration >= 1 && e.duration <= 1440)) return 'Duration must be between 1 and 1440 minutes.'
  if (!(e.violation_limit >= 1 && e.violation_limit <= 100)) return 'Warnings before ending must be between 1 and 100.'
  if (locked.value) return ''
  if (!e.questions.length) return 'Add at least one question.'
  for (const [i, q] of e.questions.entries()) {
    if (!q.text.trim()) return `Question ${i + 1} has no text.`
    if (q.question_type === 'short_answer' && !q.correct_text_answer.trim()) return `Question ${i + 1} needs a correct answer.`
    if (q.question_type !== 'short_answer') {
      if (q.options.some((o) => !o.text.trim())) return `Question ${i + 1} has an empty option.`
      if (q.options.filter((o) => o.is_correct).length !== 1) return `Question ${i + 1} needs exactly one correct option.`
    }
  }
  return ''
}

// The server returns nested errors for questions; show the first readable one.
function firstNested(value, path = '') {
  if (typeof value === 'string') return path ? `${path}: ${value}` : value
  if (Array.isArray(value)) {
    for (const [i, v] of value.entries()) {
      const found = firstNested(v, typeof v === 'object' && v && !Array.isArray(v) ? `${path ? path + ' ' : ''}${i + 1}` : path)
      if (found) return found
    }
  } else if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      const found = firstNested(v, k === 'non_field_errors' || k === 'error' ? path : `${path ? path + ' ' : ''}${k.replace(/_/g, ' ')}`)
      if (found) return found
    }
  }
  return ''
}

async function save() {
  error.value = validate()
  if (error.value) return
  saving.value = true
  const e = exam.value
  const body = {
    title: e.title.trim(), description: e.description, duration: e.duration, violation_limit: e.violation_limit,
    auto_submit_on_violation: e.auto_submit_on_violation, is_published: e.is_published, is_active: e.is_active,
    start_time: fromLocalInput(startLocal.value), end_time: fromLocalInput(endLocal.value),
  }
  if (!locked.value) {
    body.questions = e.questions.map((q, i) => ({
      text: q.text.trim(), question_type: q.question_type, points: q.points, negative_points: q.negative_points, order: i,
      explanation: q.explanation, correct_text_answer: q.question_type === 'short_answer' ? q.correct_text_answer.trim() : '',
      options: q.question_type === 'short_answer' ? [] : q.options.map((o) => ({ text: o.text.trim(), is_correct: o.is_correct })),
    }))
  }
  try {
    if (isNew) {
      const res = await examApi.create(body)
      toast.success('Exam created')
      router.replace({ name: 'org-exam', params: { slug, examId: res.exam_id } })
    } else {
      await examApi.update(examId, body)
      toast.success('Exam saved')
      router.replace({ name: 'org-exam', params: { slug, examId } })
    }
  } catch (err) {
    error.value = err.status === 400 && err.fields ? firstNested(err.raw) || err.message : err.message
  } finally {
    saving.value = false
  }
}

onMounted(() => { if (!isNew) load() })
</script>
