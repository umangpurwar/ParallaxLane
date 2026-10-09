import { beforeEach, describe, expect, it } from 'vitest'
import { http, plain, tokens, normaliseError, setSessionExpiredHandler } from '@/api/client'

function reply(config, status, data) {
  const response = { status, data, headers: {}, config, statusText: String(status) }
  if (status >= 400) {
    const error = new Error(`HTTP ${status}`)
    error.response = response
    error.config = config
    return Promise.reject(error)
  }
  return Promise.resolve(response)
}

describe('api client', () => {
  beforeEach(() => sessionStorage.clear())

  it('refreshes once for parallel 401s and retries every request', async () => {
    tokens.set('old', 'refresh-1')
    let refreshCalls = 0
    plain.defaults.adapter = async (config) => {
      refreshCalls += 1
      await new Promise((r) => setTimeout(r, 10))
      return reply(config, 200, { access: 'new', refresh: 'refresh-2' })
    }
    http.defaults.adapter = (config) =>
      config.headers.Authorization === 'Bearer new' ? reply(config, 200, { ok: true }) : reply(config, 401, { detail: 'expired' })

    const results = await Promise.all([http.get('a/'), http.get('b/'), http.get('c/')])
    expect(results.every((r) => r.data.ok)).toBe(true)
    expect(refreshCalls).toBe(1)
    expect(tokens.get()).toEqual({ access: 'new', refresh: 'refresh-2' })
  })

  it('ends the session when the refresh token is rejected', async () => {
    tokens.set('old', 'bad')
    let expired = false
    setSessionExpiredHandler(() => { expired = true })
    plain.defaults.adapter = (config) => reply(config, 401, { detail: 'Token is invalid' })
    http.defaults.adapter = (config) => reply(config, 401, { detail: 'expired' })
    await expect(http.get('a/')).rejects.toMatchObject({ status: 401 })
    expect(expired).toBe(true)
    expect(tokens.get()).toEqual({})
  })

  it('normalises server, validation and network errors', () => {
    expect(normaliseError({ response: { status: 409, data: { error: 'Name taken', code: 'name_taken' } } }))
      .toMatchObject({ code: 'name_taken', message: 'Name taken', status: 409 })
    expect(normaliseError({ response: { status: 400, data: { end_time: ['must be after start_time'] } } }).message)
      .toBe('end time: must be after start_time')
    expect(normaliseError({ response: { status: 429, data: {} } }).code).toBe('rate_limited')
    expect(normaliseError({}).code).toBe('network')
  })
})
