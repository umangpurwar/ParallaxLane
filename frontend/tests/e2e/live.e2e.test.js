// @vitest-environment node
// Drives the real backend through the dashboard's own API modules.
// Run: E2E_API_BASE=http://127.0.0.1:8000/api/ E2E_SUPERADMIN_EMAIL=... E2E_SUPERADMIN_PASSWORD=... E2E_MAIL_LOG=/path/to/django.log npx vitest run tests/e2e
import { readFileSync } from 'node:fs'
import { beforeAll, describe, expect, it, vi } from 'vitest'

const BASE = process.env.E2E_API_BASE
const run = BASE ? describe : describe.skip

function memoryStorage() {
  const data = new Map()
  return { getItem: (k) => data.get(k) ?? null, setItem: (k, v) => data.set(k, String(v)), removeItem: (k) => data.delete(k), clear: () => data.clear() }
}

function latestOtp(email) {
  const log = readFileSync(process.env.E2E_MAIL_LOG, 'utf8')
  const blocks = log.split(/(?=Subject:)/).filter((b) => b.includes(`To: ${email}`))
  const match = blocks.at(-1)?.match(/\b(\d{6})\b/)
  if (!match) throw new Error(`no OTP for ${email} in mail log`)
  return match[1]
}

run('dashboard against the live backend', () => {
  let api, tokens, session
  const stamp = Date.now()
  const applicant = `head${stamp}@college.test`
  const orgName = `Riverside College ${String(stamp).slice(-6).replace(/\d/g, (d) => 'ABCDEFGHIJ'[d])}`
  let orgId, slug, examId

  beforeAll(async () => {
    vi.stubGlobal('sessionStorage', memoryStorage())
    vi.stubEnv('VITE_API_BASE_URL', BASE)
    api = await import('@/api/endpoints')
    ;({ tokens } = await import('@/api/client'))
    ;({ session } = await import('@/stores/session'))
  })

  async function signInAs(email, password) {
    session.reset()
    return session.login(email, password)
  }

  it('applicant registers with an emailed code and applies', async () => {
    await api.auth.sendOtp(applicant, 'register')
    const data = await api.auth.verifyRegister({ email: applicant, otp: latestOtp(applicant), name: 'Head Teacher', password: 'Applicant-pass-2026' })
    tokens.set(data.access, data.refresh)
    await session.load(true)
    expect(session.homeRoute().name).toBe('apply')
    const app = await api.applications.submit({ name: orgName, description: 'Weekly tests', website: 'https://college.test' })
    expect(app.status).toBe('pending')
    orgId = app.id
    slug = app.slug
    await session.load(true)
    expect(session.homeRoute().name).toBe('application')
    await expect(api.org.overview(slug)).rejects.toMatchObject({ status: 403 })
  })

  it('super admin sees the application and approves it', async () => {
    const me = await signInAs(process.env.E2E_SUPERADMIN_EMAIL, process.env.E2E_SUPERADMIN_PASSWORD)
    expect(me.is_super_admin).toBe(true)
    const stats = await api.platform.stats()
    expect(stats.organisations.pending).toBeGreaterThan(0)
    const list = await api.platform.organisations({ status: 'pending', search: orgName })
    expect(list.results.map((o) => o.id)).toContain(orgId)
    await expect(api.platform.act(orgId, 'reject', '')).rejects.toMatchObject({ code: 'note_required' })
    const approved = await api.platform.act(orgId, 'approve', 'Verified by phone')
    expect(approved.status).toBe('approved')
    await expect(api.platform.act(orgId, 'approve', '')).rejects.toMatchObject({ code: 'invalid_transition' })
    const planned = await api.platform.setPlan(orgId, { plan: 'free', max_exams: 5 })
    expect(planned.limits.max_exams).toBe(5)
  })

  it('organisation admin runs the organisation', async () => {
    await signInAs(applicant, 'Applicant-pass-2026')
    expect(session.homeRoute()).toEqual({ name: 'org-overview', params: { slug } })
    await expect(api.platform.stats()).rejects.toMatchObject({ status: 403 })
    await api.org.switchTo(slug)
    const overview = await api.org.overview(slug)
    expect(overview.your_role).toBe('owner')

    const sent = await api.org.invite(slug, { email: `student${stamp}@college.test`, role: 'candidate', expiry_days: 7 })
    expect(sent.status).toBe('invite created')
    const pending = await api.org.invites(slug, { status: 'pending' })
    expect(pending.count).toBe(1)
    const revoked = await api.org.revokeInvite(slug, pending.results[0].id)
    expect(revoked.status).toBe('revoked')

    const start = new Date(Date.now() + 3600e3).toISOString()
    const end = new Date(Date.now() + 7200e3).toISOString()
    const created = await api.exams.create({
      title: 'Unit test 1', description: '', duration: 30, violation_limit: 3, auto_submit_on_violation: true, is_published: true,
      start_time: start, end_time: end,
      questions: [
        { text: '2 + 2?', question_type: 'mcq', points: 2, negative_points: 0, order: 0, explanation: '', correct_text_answer: '',
          options: [{ text: '4', is_correct: true }, { text: '5', is_correct: false }] },
      ],
    })
    examId = created.exam_id
    const shortAnswer = { text: 'Capital of France?', question_type: 'short_answer', points: 1, negative_points: 0, order: 1, explanation: '', correct_text_answer: 'Paris', options: [] }
    const { features } = await api.org.overview(slug)
    expect(features.allowed_question_types).toEqual(['mcq'])
    await expect(api.exams.update(examId, { questions: [shortAnswer] })).rejects.toMatchObject({ status: 400 })
    const detail = await api.exams.detail(examId)
    expect(detail.questions[0].options.find((o) => o.is_correct).text).toBe('4')
    expect(detail.has_attempts).toBe(false)
    await expect(api.exams.create({ title: 'bad', duration: 10, start_time: end, end_time: start, questions: [] }))
      .rejects.toMatchObject({ status: 400 })
    expect((await api.exams.list()).map((e) => e.id)).toContain(examId)
    expect((await api.exams.toggle(examId)).is_active).toBe(!detail.is_active)
    expect(await api.exams.results(examId)).toEqual([])
    expect(await api.exams.live(examId)).toEqual([])
    const csv = await api.exams.exportCsv(examId)
    expect(String(csv)).toContain('exam')

    const profile = await api.org.updateProfile(slug, { contact_phone: '+91 20 1234 5678' })
    expect(profile.contact_phone).toBe('+91 20 1234 5678')
    const code = await api.org.updateJoinCode(slug, { join_code_enabled: true })
    expect(code.join_code_enabled).toBe(true)
    const members = await api.org.members(slug)
    expect(members[0].role).toBe('owner')
    const audit = await api.org.auditLogs(slug, { search: 'student' })
    expect(audit.results.map((e) => e.action)).toEqual(expect.arrayContaining(['invite_revoked', 'invite_created']))
  })

  it('suspension locks the organisation admin out until reactivated', async () => {
    await signInAs(process.env.E2E_SUPERADMIN_EMAIL, process.env.E2E_SUPERADMIN_PASSWORD)
    expect((await api.platform.act(orgId, 'suspend', 'Fees unpaid')).status).toBe('suspended')
    const log = await api.platform.auditLogs({ organisation: orgId })
    expect(log.results[0].action).toBe('organisation_suspend')

    await signInAs(applicant, 'Applicant-pass-2026')
    await expect(api.org.overview(slug)).rejects.toMatchObject({ status: 403 })
    await expect(api.exams.list()).rejects.toMatchObject({ code: 'organisation_unavailable' })
    expect(session.homeRoute().name).toBe('application')

    await signInAs(process.env.E2E_SUPERADMIN_EMAIL, process.env.E2E_SUPERADMIN_PASSWORD)
    expect((await api.platform.act(orgId, 'reactivate', '')).status).toBe('approved')
  })
})
