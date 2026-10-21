// Every backend call the dashboard makes, grouped by area. Components never build URLs themselves.
import { http, publicPost } from './client'

const get = async (url, params) => (await http.get(url, { params })).data
const post = async (url, body) => (await http.post(url, body)).data
const patch = async (url, body) => (await http.patch(url, body)).data
const del = async (url) => (await http.delete(url)).data

export const auth = {
  login: (email, password) => publicPost('login/', { email, password }),
  sendOtp: (email, mode) => publicPost('accounts/send-otp/', { email, mode }),
  verifyRegister: (body) => publicPost('accounts/verify-otp-register/', body),
  verifyForgot: (body) => publicPost('accounts/verify-otp-forgot/', body),
  logout: (refresh) => post('accounts/logout/', { refresh }),
  me: () => get('accounts/me/'),
}

export const applications = {
  submit: (body) => post('organisations/create/', body),
  mine: () => get('organisations/applications/mine/'),
  update: (id, body) => patch(`organisations/applications/${id}/`, body),
  resubmit: (id, body) => post(`organisations/applications/${id}/resubmit/`, body),
}

export const platform = {
  stats: () => get('master-admin/stats/'),
  organisations: (params) => get('master-admin/organisations/', params),
  organisation: (id) => get(`master-admin/organisations/${id}/`),
  act: (id, action, note) => post(`master-admin/organisations/${id}/${action}/`, { note }),
  auditLogs: (params) => get('master-admin/audit-logs/', params),
  setApplicationsOpen: (open) => patch('master-admin/settings/organisation-creation/', { organisation_creation_enabled: open }),
}

export const org = {
  switchTo: (slug) => post(`organisations/${slug}/switch/`),
  overview: (slug) => get(`organisations/${slug}/overview/`),
  updateProfile: (slug, body) => patch(`organisations/${slug}/profile/`, body),
  members: (slug) => get(`organisations/${slug}/members/`),
  setExamAccess: (slug, id, enabled) => post(`organisations/${slug}/members/${id}/toggle-exam-access/`, { is_exam_enabled: enabled }),
  setMemberActive: (slug, id, active) => post(`organisations/${slug}/members/${id}/${active ? 'activate' : 'deactivate'}/`),
  invites: (slug, params) => get(`organisations/${slug}/invites/`, params),
  invite: (slug, body) => post(`organisations/${slug}/invite/`, body),
  revokeInvite: (slug, id) => post(`organisations/${slug}/invites/${id}/revoke/`),
  joinCode: (slug) => get(`organisations/${slug}/join-code/`),
  updateJoinCode: (slug, body) => post(`organisations/${slug}/join-code/`, body),
  devices: (slug, status) => get(`organisations/${slug}/devices/`, { status }),
  decideDevice: (slug, id, decision) => post(`organisations/${slug}/devices/${id}/${decision}/`),
  auditLogs: (slug, params) => get(`organisations/${slug}/audit-logs/`, params),
}

// Exam endpoints act on the organisation the account last switched to (org.switchTo).
export const exams = {
  list: () => get('admin/exam/list/'),
  detail: (id) => get(`admin/exam/${id}/`),
  create: (body) => post('admin/exam/create/', body),
  update: (id, body) => patch(`admin/exam/${id}/update/`, body),
  remove: (id) => del(`admin/exam/${id}/delete/`),
  toggle: (id) => post(`admin/exam/${id}/toggle/`),
  results: (id) => get(`admin/exam/${id}/results/`),
  live: (id) => get(`admin/exam/${id}/live/`),
  clearViolations: (id, username) => post(`admin/exam/${id}/user/${encodeURIComponent(username)}/clear/`),
  async exportCsv(id) {
    const response = await http.get(`admin/exam/${id}/export/`, { responseType: 'blob' })
    return response.data
  },
}
