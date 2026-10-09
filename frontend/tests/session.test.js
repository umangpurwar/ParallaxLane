import { describe, expect, it, vi } from 'vitest'

vi.mock('@/api/endpoints', () => ({ auth: { me: vi.fn() } }))
const { auth } = await import('@/api/endpoints')
const { session } = await import('@/stores/session')

async function homeFor(me) {
  auth.me.mockResolvedValueOnce(me)
  await session.load(true)
  return session.homeRoute()
}

const base = { is_super_admin: false, memberships: [], applications: [] }

describe('session.homeRoute uses only server data', () => {
  it('routes each kind of account to its panel', async () => {
    expect((await homeFor({ ...base, is_super_admin: true })).name).toBe('platform-overview')
    const admin = { slug: 'a', is_admin: true, status: 'approved' }
    expect(await homeFor({ ...base, memberships: [admin] })).toEqual({ name: 'org-overview', params: { slug: 'a' } })
    expect((await homeFor({ ...base, memberships: [admin, { ...admin, slug: 'b' }] })).name).toBe('org-picker')
    expect((await homeFor({ ...base, applications: [{ status: 'pending' }] })).name).toBe('application')
    expect((await homeFor({ ...base, memberships: [{ slug: 'c', is_admin: false, status: 'approved' }] })).name).toBe('members-only')
    expect((await homeFor(base)).name).toBe('apply')
  })

  it('does not open the org panel for an organisation that is not approved', async () => {
    const route = await homeFor({ ...base, memberships: [{ slug: 'p', is_admin: true, status: 'pending' }], applications: [{ status: 'pending' }] })
    expect(route.name).toBe('application')
  })
})
