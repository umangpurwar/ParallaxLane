import { createRouter, createWebHistory } from "vue-router"
import { STAFF_ROLES } from "@/services/api"

import HomeView from "../views/HomeView.vue"
import LoginView from "../views/LoginView.vue"
import RegisterView from "../views/RegisterView.vue"
import ExamDashboard from "../views/ExamDashboard.vue"
import ExamPage from "../views/ExamPage.vue"
import AdminDashboard from "../views/AdminDashboard.vue"
import UnauthorizedView from "../views/UnauthorizedView.vue"
import OrgHomeView from "../views/OrgHomeView.vue"
import OrgCreateView from "../views/OrgCreateView.vue"

const routes = [
  { path: "/", component: HomeView },
  { path: "/login", name: "Login", component: LoginView },
  { path: "/register", component: RegisterView },
  { path: "/unauthorized", component: UnauthorizedView },

  { path: "/create-org", component: OrgCreateView, meta: { requiresAuth: true } },

  {
    path: "/org-home",
    component: OrgHomeView,
    meta: { requiresAuth: true }
  },

  {
    path: "/join-org",
    component: () => import("../views/JoinOrgView.vue"),
    meta: { requiresAuth: true }
  },

  {
    path: "/dashboard",
    component: ExamDashboard,
    meta: { requiresAuth: true, requiresOrg: true, requiresCandidate: true }
  },

  {
    path: "/exam/:id",
    name: "Exam",
    component: ExamPage,
    meta: { requiresAuth: true, requiresOrg: true, requiresCandidate: true }
  },

  {
    path: "/auth/google",
    name: "GoogleAuth",
    component: () => import("../views/GoogleAuth.vue")
  },

  {
    path: "/admin",
    component: AdminDashboard,
    meta: { requiresAuth: true, requiresOrg: true, requiresStaff: true }
  },

  {
    path: "/org-settings",
    component: () => import("../views/OrgSettingsView.vue"),
    meta: { requiresAuth: true, requiresOrg: true, requiresStaff: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

let isBrowserNavigation = false

window.addEventListener('popstate', () => {
  isBrowserNavigation = true
})

const clearExamState = () => {
  localStorage.removeItem("attempt_id")
  localStorage.removeItem("active_exam_id")

  Object.keys(localStorage).forEach(key => {
    if (key.startsWith("exam_state_")) {
      localStorage.removeItem(key)
    }
  })
}

const ORG_HUB_PATHS = ["/org-home", "/create-org", "/join-org", "/org-settings"]

router.beforeEach((to, from) => {
  const token = localStorage.getItem("access_token") || localStorage.getItem("token")
  const orgSlug = localStorage.getItem("org_slug")
  const orgRole = localStorage.getItem("org_role")

  if (isBrowserNavigation && token) {
    isBrowserNavigation = false

    if (from.path.startsWith("/exam")) {
      clearExamState()
      return "/dashboard"
    }
  }

  isBrowserNavigation = false

  if (to.meta.requiresAuth && !token) {
    if (to.path !== '/login' && to.path !== '/') {
      return "/unauthorized"
    }
    return "/login"
  }

  if (token && (to.path === "/login" || to.path === "/register")) {
    return "/org-home"
  }

  if (token && !orgSlug && to.meta.requiresOrg) {
    return "/org-home"
  }

  if (token && !orgSlug && !ORG_HUB_PATHS.includes(to.path)) {
    return "/org-home"
  }

  if (token && orgSlug && to.path === "/create-org") {
    return "/org-home"
  }

  if (to.meta.requiresStaff && !STAFF_ROLES.includes(orgRole)) {
    return "/org-home"
  }

  if (to.meta.requiresCandidate && orgRole !== "candidate") {
    return "/org-home"
  }

  return true
})

export default router

