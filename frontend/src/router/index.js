import { createRouter, createWebHistory } from "vue-router"

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

  { path: "/create-org", component: OrgCreateView },

  { path: "/dashboard", component: ExamDashboard, meta: { requiresAuth: true } },
  { path: "/exam/:id", name: "Exam", component: ExamPage, meta: { requiresAuth: true } },

  {
    path: "/auth/google",
    name: "GoogleAuth",
    component: () => import("../views/GoogleAuth.vue")
  },

  {
    path: "/org-home",
    component: OrgHomeView,
    meta: { requiresAuth: true }
  },

  {
    path: "/join-org",
    component: () => import("../views/JoinOrgView.vue")
  },

  { path: "/admin", component: AdminDashboard, meta: { requiresAuth: true, isAdmin: true } }
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

router.beforeEach((to, from) => {
  const token = localStorage.getItem("access_token") || localStorage.getItem("token")
  const orgSlug = localStorage.getItem("org_slug")
  const orgRole = localStorage.getItem("org_role")

  const isAdmin = orgRole === "owner" || orgRole === "admin"

  // Handle browser back navigation (exam safety)
  if (isBrowserNavigation && token) {
    isBrowserNavigation = false

    if (from.path.startsWith("/exam")) {
      clearExamState()
      return "/dashboard"
    }
  }

  isBrowserNavigation = false

  // Auth check
  if (to.meta.requiresAuth && !token) {
    if (to.path !== '/login' && to.path !== '/') {
      return "/unauthorized"
    }
    return "/login"
  }

  // Prevent logged-in users from going to login/register
  if (token && (to.path === "/login" || to.path === "/register")) {
    return "/org-home"
  }

  // Org onboarding flow
  if (token && !orgSlug) {
    if (to.path !== "/org-home" && to.path !== "/create-org" && to.path !== "/join-org") {
      return "/org-home"
    }
  }

  // Prevent going back to create-org after org exists
  if (token && orgSlug && to.path === "/create-org") {
    return "/org-home"
  }

  // Admin check
  if (to.meta.isAdmin && !isAdmin) {
    return "/unauthorized"
  }

  return true
})

export default router