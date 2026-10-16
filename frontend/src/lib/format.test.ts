import { describe, expect, it } from 'vitest'
import { formatDuration, formatMiles, hoursBetween } from './format'

describe('formatMiles', () => {
  it('rounds to whole miles', () => {
    expect(formatMiles(534.8)).toBe('535 mi')
    expect(formatMiles(2209.3)).toBe('2,209 mi')
  })
})

describe('formatDuration', () => {
  it('shows hours and minutes', () => {
    expect(formatDuration(27_243)).toBe('7 h 34 m')
  })

  it('shows only minutes under an hour', () => {
    expect(formatDuration(1_500)).toBe('25 m')
  })
})

describe('hoursBetween', () => {
  it('returns fractional hours', () => {
    expect(hoursBetween('2026-10-16T14:00:00Z', '2026-10-16T17:51:00Z')).toBeCloseTo(3.85)
  })
})
