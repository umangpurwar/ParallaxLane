<template>
  <div class="max-w-3xl pb-10">
    <div class="mb-8 flex justify-between items-center">
      <div>
        <h2 class="text-3xl font-medium tracking-tighter text-brutal-ink">Create Assessment</h2>
        <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500 mt-1">Configure parameters and MCQs</p>
      </div>
      <button @click="$emit('change-tab', 'exams')" class="text-[10px] uppercase tracking-widest font-bold text-gray-500 hover:text-brutal-ink transition-colors">
        Cancel &larr;
      </button>
    </div>

    <form @submit.prevent="submitExam" class="bg-white border border-brutal-border p-8 flex flex-col gap-8">
      
      <div class="flex flex-col gap-6 border-b border-brutal-border/30 pb-8">
        <h3 class="text-[10px] uppercase tracking-super-wide font-bold text-brutal-red">1. Core Details</h3>
        
        <div class="flex flex-col gap-2">
          <label class="text-[9px] uppercase tracking-widest font-bold text-gray-500">Exam Title *</label>
          <input v-model="formData.title" type="text" required placeholder="e.g. Advanced Data Structures" class="w-full border-b border-brutal-border px-0 py-2 text-sm text-brutal-ink focus:outline-none focus:border-brutal-red bg-transparent" />
        </div>

        <div class="flex flex-col gap-2">
          <label class="text-[9px] uppercase tracking-widest font-bold text-gray-500">Description</label>
          <textarea v-model="formData.description" rows="2" placeholder="Brief instructions..." class="w-full border-b border-brutal-border px-0 py-2 text-sm text-brutal-ink focus:outline-none focus:border-brutal-red bg-transparent resize-none"></textarea>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="flex flex-col gap-2">
            <label class="text-[9px] uppercase tracking-widest font-bold text-gray-500">Duration (Mins) *</label>
            <input v-model.number="formData.duration" type="number" required min="1" class="w-full border-b border-brutal-border px-0 py-2 text-sm text-brutal-ink focus:outline-none focus:border-brutal-red bg-transparent" />
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-[9px] uppercase tracking-widest font-bold text-gray-500">Start Date/Time</label>
            <input v-model="formData.start_time" type="datetime-local" class="w-full border-b border-brutal-border px-0 py-2 text-sm text-brutal-ink focus:outline-none focus:border-brutal-red bg-transparent" />
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-[9px] uppercase tracking-widest font-bold text-gray-500">End Date/Time</label>
            <input v-model="formData.end_time" type="datetime-local" class="w-full border-b border-brutal-border px-0 py-2 text-sm text-brutal-ink focus:outline-none focus:border-brutal-red bg-transparent" />
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-6 border-b border-brutal-border/30 pb-8">
        <div class="flex justify-between items-center">
  <h3 class="text-[10px] uppercase tracking-super-wide font-bold text-brutal-red">
    2. Questionnaire ({{ formData.questions.length }})
  </h3>

        <div class="flex gap-2 items-center">

            <!-- Input (same brutal style & size) -->
            <input
              v-model="questionCount"
              type="text"
              placeholder="1"
              class="w-[80px] bg-white border-2 border-brutal-ink py-1 text-center text-brutal-ink font-bold tracking-widest text-[10px] focus:outline-none"
              />

            <!-- Button -->
            <button
            type="button"
            @click="handleAddQuestion"
            :disabled="isAddDisabled"
            class="px-3 py-1 border-2 border-brutal-ink text-[9px] uppercase tracking-widest font-bold transition-all"
            :class="isAddDisabled 
            ? 'bg-gray-300 text-gray-500 border-gray-300 cursor-not-allowed' 
            : 'bg-brutal-ink text-white hover:bg-gray-800 cursor-pointer'"
            >
             + Add Question
          </button>

          </div>
        </div>

        <div v-for="(q, index) in formData.questions" :key="index" class="bg-gray-50 p-6 border border-brutal-border relative">
          <button type="button" @click="removeQuestion(index)" class="absolute top-4 right-4 text-gray-400 hover:text-brutal-red font-bold text-sm">X</button>
          
          <div class="flex flex-col gap-4">
            <div class="flex flex-col gap-2">
              <label class="text-[9px] uppercase tracking-widest font-bold text-gray-500">Q{{ index + 1 }}. Question Text</label>
              <input v-model="q.text" type="text" required class="w-full border-b border-gray-300 px-0 py-2 text-sm focus:outline-none focus:border-brutal-ink bg-transparent" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1">
                <label class="text-[9px] uppercase font-bold text-gray-400">Option A</label>
                <input v-model="q.option_a" type="text" required class="border-b border-gray-300 py-1 text-sm bg-transparent focus:outline-none focus:border-brutal-ink" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[9px] uppercase font-bold text-gray-400">Option B</label>
                <input v-model="q.option_b" type="text" required class="border-b border-gray-300 py-1 text-sm bg-transparent focus:outline-none focus:border-brutal-ink" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[9px] uppercase font-bold text-gray-400">Option C</label>
                <input v-model="q.option_c" type="text" required class="border-b border-gray-300 py-1 text-sm bg-transparent focus:outline-none focus:border-brutal-ink" />
              </div>
              <div class="flex flex-col gap-1">
                <label class="text-[9px] uppercase font-bold text-gray-400">Option D</label>
                <input v-model="q.option_d" type="text" required class="border-b border-gray-300 py-1 text-sm bg-transparent focus:outline-none focus:border-brutal-ink" />
              </div>
            </div>

            <div class="flex flex-col gap-2 mt-2">
              <label class="text-[9px] uppercase tracking-widest font-bold text-brutal-ink">Correct Answer</label>
              <select v-model="q.correct_answer" required class="w-full p-2 border border-brutal-border text-sm bg-white focus:outline-none focus:border-brutal-red">
                <option disabled value="">Select the correct option...</option>
                <option value="a">Option A</option>
                <option value="b">Option B</option>
                <option value="c">Option C</option>
                <option value="d">Option D</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div v-if="errorMessage" class="text-[10px] uppercase font-bold text-brutal-red">{{ errorMessage }}</div>
      
      <button type="submit" :disabled="isSubmitting" class="w-full bg-brutal-ink text-white py-4 text-[10px] uppercase tracking-widest font-bold hover:bg-brutal-red transition-colors">
        {{ isSubmitting ? 'Deploying...' : 'Deploy Exam & Questions' }}
      </button>

    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import api from '@/services/api';
const isEditMode = ref(false);
const editExamId = ref(null);

const emit = defineEmits(['change-tab']);


const isSubmitting = ref(false);
const errorMessage = ref('');

const formData = ref({
  title: '',
  description: '',
  duration: 60,
  start_time: '',
  end_time: '',
  questions: [
    { text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_answer: '' }
  ]
});

const questionCount = ref("1")

const isAddDisabled = computed(() => {
  const num = parseInt(questionCount.value)
  return isNaN(num) || num <= 0
})

const handleAddQuestion = () => {
  const count = parseInt(questionCount.value)
  if (!count || count <= 0) return

  for (let i = 0; i < count; i++) {
    addQuestion()
  }
}

const addQuestion = () => {
  formData.value.questions.push({ text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_answer: '' });
};

const removeQuestion = (index) => {
  formData.value.questions.splice(index, 1);
};

const submitExam = async () => {
  isSubmitting.value = true;
  errorMessage.value = '';

  try {
    // Prepare payload
    const payload = JSON.parse(JSON.stringify(formData.value));

    if (payload.start_time) {
      payload.start_time = new Date(payload.start_time).toISOString();
    }

    if (payload.end_time) {
      payload.end_time = new Date(payload.end_time).toISOString();
    } else {
      const end = new Date();
      end.setDate(end.getDate() + 7);
      payload.end_time = end.toISOString();
    }

    if (!payload.start_time) {
      payload.start_time = new Date().toISOString();
    }

    // VALIDATE QUESTIONS (Using the UI format)
    const hasInvalidQuestion = payload.questions.some(q =>
      !q.text ||
      !q.option_a ||
      !q.option_b ||
      !q.option_c ||
      !q.option_d ||
      !q.correct_answer
    );

    if (hasInvalidQuestion) {
      errorMessage.value = "Fill all question fields properly";
      isSubmitting.value = false;
      return;
    }

    // --- NEW FORMAT TRANSFORMATION ---
    // Safely transforms the UI format into the new backend schema
    payload.questions = payload.questions.map(q => {
      // Setup default extensible structure for future question types
      const type = q.question_type || "mcq"; 
      
      let formattedQuestion = {
        text: q.text,
        question_type: type,
        points: 1, // Defaulting to 1 point as requested
      };

      if (type === "mcq") {
        formattedQuestion.options = [
          { text: q.option_a, is_correct: q.correct_answer === 'a' },
          { text: q.option_b, is_correct: q.correct_answer === 'b' },
          { text: q.option_c, is_correct: q.correct_answer === 'c' },
          { text: q.option_d, is_correct: q.correct_answer === 'd' }
        ];
      } else if (type === "short_answer") {
        // Future Support Example
        // formattedQuestion.correct_text_answer = q.correct_text_answer;
      } else if (type === "file_upload") {
        // Future Support Example
      }

      return formattedQuestion;
    });
    // --- END TRANSFORMATION ---

    if (isEditMode.value) {
      await api.patch(`admin/exam/${editExamId.value}/update/`, payload);
    } else {
      await api.post('admin/exam/create/', payload);
    }

    // SUCCESS
    isEditMode.value = false;
    editExamId.value = null;
    
    emit('change-tab', 'exams');

  } catch (error) {
    console.error("NETWORK ERROR:", error);
    errorMessage.value = 'Network error occurred.';
  } finally {
    isSubmitting.value = false;
  }
};

onMounted(() => {
  const editData = localStorage.getItem("edit_exam");

  if (editData) {
    const exam = JSON.parse(editData);

    isEditMode.value = true;
    editExamId.value = exam.id;

    formData.value.title = exam.title;
    formData.value.description = exam.description;
    formData.value.duration = exam.duration;

    formData.value.start_time = exam.start_time ? exam.start_time.slice(0, 16): '';
    formData.value.end_time = exam.end_time ? exam.end_time.slice(0, 16): '';

    formData.value.questions = [];
    if (exam.questions && exam.questions.length) {
      formData.value.questions = exam.questions.map(q => {
        // Fallback backward-compatibility: 
        // If the backend returns the NEW format, seamlessly convert it back to the UI format.
        if (q.question_type === 'mcq' && q.options) {
          const correctIdx = q.options.findIndex(o => o.is_correct);
          const correctLetter = ['a', 'b', 'c', 'd'][correctIdx] || '';
          
          return {
            text: q.text || '',
            option_a: q.options[0]?.text || '',
            option_b: q.options[1]?.text || '',
            option_c: q.options[2]?.text || '',
            option_d: q.options[3]?.text || '',
            correct_answer: correctLetter
          };
        }
        
        // Use existing structure if it's already using old fields
        return { ...q };
      });
    }

    localStorage.removeItem("edit_exam");
  }
});
</script>