<template>
  <PageHeader title="Audit log" description="Administrative actions in this organisation, newest first." />
  <AuditTable :fetcher="(params) => org.auditLogs(slug, params)" search-placeholder="Search target or person" />
</template>

<script setup>
import { useRoute } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import AuditTable from '@/components/AuditTable.vue'
import { org } from '@/api/endpoints'
const slug = useRoute().params.slug
</script>
