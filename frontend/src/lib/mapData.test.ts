import { describe, expect, it } from 'vitest'
import type { Heatmap, PlannedRoute } from '../api/types'
import { boundsOf, cellRadius, heatmapToGeoJson, riskAtHour, riskColor } from './mapData'
import { RISK_STYLE } from './risk'

const route = (geometry: [number, number][]) => ({ geometry }) as PlannedRoute

describe('heatmapToGeoJson', () => {
  it('turns hourly risk into h0..hN properties', () => {
    const heatmap: Heatmap = {
      start_time: '2026-10-16T05:00:00Z',
      hours: 3,
      cell_size_deg: 0.2,
      points: [{ lat: 40, lon: -105, risk: [0, 2, 4] }],
    }
    const [feature] = heatmapToGeoJson(heatmap).features
    expect(feature.properties).toEqual({ h0: 0, h1: 2, h2: 4 })
    expect(feature.geometry).toEqual({ type: 'Point', coordinates: [-105, 40] })
  })
})

describe('riskAtHour', () => {
  it('blends the two neighbouring hours', () => {
    expect(riskAtHour(3.25, 47)).toEqual(['+', ['*', 0.75, ['get', 'h3']], ['*', 0.25, ['get', 'h4']]])
  })

  it('never reads past the last hour', () => {
    expect(riskAtHour(47, 47)).toEqual(['+', ['*', 1, ['get', 'h47']], ['*', 0, ['get', 'h47']]])
  })
})

describe('riskColor', () => {
  it('maps 0-4 to the shared risk colours', () => {
    const expression = riskColor(['get', 'h0'])
    expect(expression.slice(3)).toEqual([
      0, RISK_STYLE.LOW.color, 1, RISK_STYLE.MODERATE.color, 2, RISK_STYLE.HIGH.color,
      3, RISK_STYLE.SEVERE.color, 4, RISK_STYLE.NO_TRAVEL.color,
    ])
  })
})

describe('cellRadius', () => {
  it('doubles the radius with every zoom level', () => {
    const [, , , , atZoom0, , atZoom22] = cellRadius(0.2, 40) as number[]
    expect(atZoom22 / atZoom0).toBe(2 ** 22)
  })

  it('grows with the grid cell size', () => {
    const small = cellRadius(0.2, 40)[4] as number
    const large = cellRadius(0.6, 40)[4] as number
    expect(large / small).toBeCloseTo(3)
  })
})

describe('boundsOf', () => {
  it('covers every route', () => {
    const routes = [route([[-105, 39.7], [-108, 41]]), route([[-111.9, 40.7]])]
    expect(boundsOf(routes)).toEqual([[-111.9, 39.7], [-105, 41]])
  })
})
