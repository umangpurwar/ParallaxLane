<template>
  <div class="max-w-4xl mx-auto pb-10">
    <div class="mb-8">
      <h2 class="text-3xl font-medium tracking-tighter text-brutal-ink">Assessment Reports</h2>
      <p class="text-[9px] uppercase tracking-widest font-semibold text-gray-500 mt-1">
        Download professional Excel reports for HR, recruiters, and administrators
      </p>
    </div>

    <div class="space-y-6">
      <div
        v-for="exam in exams"
        :key="'rep-' + exam.id"
        class="bg-white border border-brutal-border p-6 md:p-8"
      >
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div class="min-w-0 flex-1">
            <h3 class="text-xl font-medium tracking-tight text-brutal-ink">{{ exam.title }}</h3>
            <p class="text-[10px] uppercase tracking-widest font-semibold text-gray-500 mt-1">
              Scheduled: {{ exam.date }}
            </p>
            <p class="text-sm text-gray-600 mt-3 leading-relaxed max-w-xl">
              Generates a two-sheet workbook: Candidate Assessment Report and Exam Statistics.
              Includes scores, pass/fail status, proctoring risk, and violation summaries.
            </p>
          </div>

          <button
            @click="downloadReport(exam.id)"
            :disabled="downloadingId === exam.id"
            class="shrink-0 px-6 py-3 bg-brutal-ink text-white text-[9px] uppercase tracking-widest font-bold hover:bg-brutal-red transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg
              v-if="downloadingId !== exam.id"
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="square"
                stroke-linejoin="miter"
                stroke-width="2"
                d="M12 10v6m0 0l-3-3m3 3l3-3M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1"
              />
            </svg>
            {{ downloadingId === exam.id ? 'Generating...' : 'Download Excel Report' }}
          </button>
        </div>

        <p v-if="errorByExam[exam.id]" class="mt-4 text-sm text-brutal-red font-medium">
          {{ errorByExam[exam.id] }}
        </p>
      </div>

      <div
        v-if="!exams || exams.length === 0"
        class="py-12 text-center text-sm text-gray-500 border border-dashed border-brutal-border"
      >
        No exams available for reporting.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import api from '@/services/api';

defineProps({
  exams: Array,
});

const downloadingId = ref(null);
const errorByExam = reactive({});

const downloadReport = async (examId) => {
  downloadingId.value = examId;
  errorByExam[examId] = '';

  try {
    const response = await api.get(`admin/exam/${examId}/export/`, {
      responseType: 'blob',
      timeout: 120000,
    });

    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'ParallaxLane_Assessment_Report.xlsx');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    console.error('Report export error:', e);
    errorByExam[examId] = 'Failed to generate report. Please try again.';
  } finally {
    downloadingId.value = null;
  }
};
</script>
