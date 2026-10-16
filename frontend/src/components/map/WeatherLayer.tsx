import type { AddLayerObject, Map } from 'maplibre-gl'
import { useEffect, useMemo, useState } from 'react'
import type { Heatmap } from '../../api/types'
import { cellRadius, heatmapToGeoJson, riskAtHour, riskColor } from '../../lib/mapData'
import { ForecastSlider } from './ForecastSlider'
import { useGeoJsonLayers } from './useGeoJsonLayers'

const SOURCE_ID = 'weather'
const LAYER_ID = 'weather-risk'
export const LAST_HOUR = 47 // the API always returns 48 hourly values

// Blurred circles coloured by the actual risk level. Overlapping circles blend into a band.
// (A density heatmap would colour by how many points overlap, not by risk.)
const LAYERS: AddLayerObject[] = [
  {
    id: LAYER_ID,
    type: 'circle',
    source: SOURCE_ID,
    paint: {
      'circle-blur': 0.7,
      'circle-opacity': 0.45,
      'circle-color': riskColor(riskAtHour(0, LAST_HOUR)),
    },
  },
]

interface Props {
  map: Map
  heatmap: Heatmap
  hour: number
  onHourChange: (hour: number) => void
}

/** The 0-48 h weather risk along the routes plus its forecast slider (ADR-0009). */
export function WeatherLayer({ map, heatmap, hour, onHourChange }: Props) {
  const data = useMemo(() => heatmapToGeoJson(heatmap), [heatmap])
  // Under the map labels, so place names stay readable. Looked up once: getStyle() is costly.
  const [labelsLayerId] = useState(
    () => map.getStyle().layers.find((layer) => layer.type === 'symbol')?.id,
  )
  useGeoJsonLayers(map, SOURCE_ID, data, LAYERS, labelsLayerId)

  // Size each circle to the grid spacing, so short and long trips both form a smooth band.
  useEffect(() => {
    const latitudes = heatmap.points.map((point) => point.lat)
    const middleLatitude = (Math.min(...latitudes) + Math.max(...latitudes)) / 2
    map.setPaintProperty(LAYER_ID, 'circle-radius', cellRadius(heatmap.cell_size_deg, middleLatitude))
  }, [map, heatmap])

  // Moving the slider only swaps one style expression: no network request and no React
  // re-render of other layers. At most one update per animation frame.
  useEffect(() => {
    const frame = requestAnimationFrame(() =>
      map.setPaintProperty(LAYER_ID, 'circle-color', riskColor(riskAtHour(hour, LAST_HOUR))),
    )
    return () => cancelAnimationFrame(frame)
  }, [map, hour])

  return (
    <ForecastSlider
      startTime={heatmap.start_time}
      lastHour={LAST_HOUR}
      hour={hour}
      onChange={onHourChange}
    />
  )
}
