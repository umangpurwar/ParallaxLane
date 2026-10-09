import { createRouter, createWebHistory } from 'vue-router'
import { session } from '@/stores/session'
import { org as orgApi } from '@/api/endpoints'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { public: true } },
  { path: '/reset-password', name: 'reset-password', component: () => import('@/views/auth/ResetPasswordView.vue'), meta: { public: true } },

  { path: '/', name: 'home', component: { render: () => null } },
  { path: '/apply', name: 'apply', component: () => import('@/views/applicant/ApplyView.vue') },
  { path: '/application', name: 'application', component: () => import('@/views/applicant/ApplicationView.vue') },
  { path: '/members-only', name: 'members-only', component: () => import('@/views/applicant/MembersOnlyView.vue') },
  { path: '/organisations', name: 'org-picker', component: () => import('@/views/org/OrgPickerView.vue') },

  {
    path: '/platform',
    component: () => import('@/components/PlatformLayout.vue'),
    meta: { panel: 'platform' },
    children: [
      { path: '', name: 'platform-overview', component: () => import('@/views/platform/PlatformOverview.vue') },
      { path: 'organisations', name: 'platform-orgs', component: () => import('@/views/platform/PlatformOrganisations.vue') },
      { path: 'organisations/:id', name: 'platform-org', component: () => import('@/views/platform/PlatformOrganisationDetail.vue') },
      { path: 'audit', name: 'platform-audit', component: () => import('@/views/platform/PlatformAudit.vue') },
    ],
  },
  {
    path: '/org/:slug',
    component: () => import('@/components/OrgLayout.vue'),
    meta: { panel: 'org' },
    children: [
      { path: '', name: 'org-overview', component: () => import('@/views/org/OrgOverview.vue') },
      { path: 'members', name: 'org-members', component: () => import('@/views/org/OrgMembers.vue') },
      { path: 'invitations', name: 'org-invites', component: () => import('@/views/org/OrgInvites.vue') },
      { path: 'devices', name: 'org-devices', component: () => import('@/views/org/OrgDevices.vue') },
      { path: 'exams', name: 'org-exams', component: () => import('@/views/org/OrgExams.vue') },
      { path: 'exams/new', name: 'org-exam-new', component: () => import('@/views/org/OrgExamEditor.vue') },
      { path: 'exams/:examId/edit', name: 'org-exam-edit', component: () => import('@/views/org/OrgExamEditor.vue') },
      { path: 'exams/:examId', name: 'org-exam', component: () => import('@/views/org/OrgExamDetail.vue') },
      { path: 'settings', name: 'org-settings', component: () => import('@/views/org/OrgSettings.vue') },
      { path: 'audit', name: 'org-audit', component: () => import('@/views/org/OrgAudit.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

// The account the backend calls "current organisation" scopes the exam endpoints.
let switchedTo = null

router.beforeEach(async (to) => {
  if (to.meta.public) {
    return session.isSignedIn() && to.name === 'login' ? { name: 'home' } : true
  }
  if (!session.isSignedIn()) return { name: 'login', query: { next: to.fullPath } }
  try {
    await session.load()
  } catch {
    session.reset()
    return { name: 'login' }
  }
  if (to.name === 'home') return session.homeRoute()

  const panel = to.matched.find((r) => r.meta.panel)?.meta.panel
  const me = session.state.me
  if (panel === 'platform' && !me.is_super_admin) return session.homeRoute()
  if (panel === 'org') {
    const slug = to.params.slug
    if (!session.adminOrgs().some((m) => m.slug === slug)) return session.homeRoute()
    if (switchedTo !== slug) {
      try {
        await orgApi.switchTo(slug)
        switchedTo = slug
      } catch {
        return session.homeRoute()
      }
    }
  }
  if (!panel) switchedTo = null
  return true
})

export default router
