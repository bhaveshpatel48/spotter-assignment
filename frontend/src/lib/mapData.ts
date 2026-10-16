// Pure conversions from API data to map data and map style expressions.

import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { FeatureCollection } from 'geojson'
import type { Checkpoint, Heatmap, PlannedRoute } from '../api/types'
import { RISK_LEVELS, RISK_STYLE } from './risk'

type Bounds = [[west: number, south: number], [east: number, north: number]]

export function routesToGeoJson(routes: PlannedRoute[]): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: routes.map((route) => ({
      type: 'Feature',
      properties: { id: route.id },
      geometry: { type: 'LineString', coordinates: route.geometry },
    })),
  }
}

export function checkpointsToGeoJson(checkpoints: Checkpoint[]): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: checkpoints.map((checkpoint) => ({
      type: 'Feature',
      properties: { index: checkpoint.index, color: RISK_STYLE[checkpoint.risk_level].color },
      geometry: { type: 'Point', coordinates: [checkpoint.lon, checkpoint.lat] },
    })),
  }
}

/** One point per grid cell, with its hourly risk as properties h0..h47 (map expressions
 * cannot read array properties). */
export function heatmapToGeoJson(heatmap: Heatmap): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: heatmap.points.map((point) => ({
      type: 'Feature',
      properties: Object.fromEntries(point.risk.map((risk, hour) => [`h${hour}`, risk])),
      geometry: { type: 'Point', coordinates: [point.lon, point.lat] },
    })),
  }
}

/** A plain loop: long trips have too many points to spread into Math.min(...). */
export function boundsOf(routes: PlannedRoute[]): Bounds {
  let [west, south, east, north] = [Infinity, Infinity, -Infinity, -Infinity]
  for (const route of routes) {
    for (const [lon, lat] of route.geometry) {
      west = Math.min(west, lon)
      east = Math.max(east, lon)
      south = Math.min(south, lat)
      north = Math.max(north, lat)
    }
  }
  return [
    [west, south],
    [east, north],
  ]
}

/** Risk (0-4) at a fractional hour, blended between the two neighbouring hours so the
 * slider fades smoothly instead of jumping. */
export function riskAtHour(hour: number, lastHour: number): ExpressionSpecification {
  const before = Math.min(Math.floor(hour), lastHour)
  const after = Math.min(before + 1, lastHour)
  const fraction = hour - before
  return [
    '+',
    ['*', 1 - fraction, ['get', `h${before}`]],
    ['*', fraction, ['get', `h${after}`]],
  ]
}

/** Colour for a risk value (0-4), using the same colours as the rest of the UI. */
export function riskColor(risk: ExpressionSpecification): ExpressionSpecification {
  const stops = RISK_LEVELS.flatMap((level, value) => [value, RISK_STYLE[level].color])
  return ['interpolate', ['linear'], risk, ...stops] as ExpressionSpecification
}

const METERS_PER_DEGREE = 111_320
// Ground metres covered by one pixel at zoom 0 on the equator (512-pixel tiles).
const METERS_PER_PIXEL_AT_ZOOM_0 = 78_271.5
const MAX_ZOOM = 22
// Weather points sit about one cell apart along each road. Circles a little over one cell wide
// merge into one band per road without smearing colour far from where it was measured.
const RADIUS_PER_CELL = 1.2

/** Circle radius in pixels that keeps one grid cell the same ground size at every zoom. */
export function cellRadius(cellSizeDeg: number, latitude: number): ExpressionSpecification {
  const metersPerPixel = METERS_PER_PIXEL_AT_ZOOM_0 * Math.cos((latitude * Math.PI) / 180)
  const radiusAtZoom0 = (RADIUS_PER_CELL * cellSizeDeg * METERS_PER_DEGREE) / metersPerPixel
  return [
    'interpolate',
    ['exponential', 2],
    ['zoom'],
    0,
    radiusAtZoom0,
    MAX_ZOOM,
    radiusAtZoom0 * 2 ** MAX_ZOOM,
  ]
}
