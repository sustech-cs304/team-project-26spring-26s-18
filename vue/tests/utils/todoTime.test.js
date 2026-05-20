import { describe, it, expect } from 'vitest'
import { BEIJING_TIMEZONE, getBeijingNowParts } from '@/utils/todoTime'

describe('todoTime utils', () => {
  it('BEIJING_TIMEZONE should be Asia/Shanghai', () => {
    expect(BEIJING_TIMEZONE).toBe('Asia/Shanghai')
  })

  it('getBeijingNowParts should return object with date/time parts', () => {
    const parts = getBeijingNowParts()
    expect(parts).toBeDefined()
    expect(typeof parts).toBe('object')
  })
})
