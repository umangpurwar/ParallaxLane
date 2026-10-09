<template>
  <PageHeader title="Audit log" description="Every administrative action on the platform, newest first." />
  <AuditTable :fetcher="platform.auditLogs" show-org search-placeholder="Search target, person or organisation" />
</template>

<script setup>
import PageHeader from '@/components/PageHeader.vue'
import AuditTable from '@/components/AuditTable.vue'
import { platform } from '@/api/endpoints'
</script>
