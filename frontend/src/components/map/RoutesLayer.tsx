import type { ExpressionSpecification } from '@maplibre/maplibre-gl-style-spec'
import type { AddLayerObject, Map, MapLayerMouseEvent } from 'maplibre-gl'
import { useEffect, useMemo } from 'react'
import type { PlannedRoute } from '../../api/types'
import { boundsOf, routesToGeoJson } from '../../lib/mapData'
import { useGeoJsonLayers } from './useGeoJsonLayers'

const SOURCE_ID = 'routes'
const LINE_ID = 'routes-line'
const SELECTED_COLOR = '#1c64d4'
const OTHER_COLOR = '#7b8794'

const LAYERS: AddLayerObject[] = [
  {
    id: 'routes-casing',
    type: 'line',
    source: SOURCE_ID,
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#ffffff', 'line-width': 8 },
  },
  {
    id: LINE_ID,
    type: 'line',
    source: SOURCE_ID,
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': OTHER_COLOR, 'line-width': 4 },
  },
]

interface Props {
  map: Map
  routes: PlannedRoute[]
  selectedId: string
  onSelect: (id: string) => void
}

export function RoutesLayer({ map, routes, selectedId, onSelect }: Props) {
  const data = useMemo(() => routesToGeoJson(routes), [routes])
  useGeoJsonLayers(map, SOURCE_ID, data, LAYERS)

  // Zoom to the trip whenever a new plan arrives.
  useEffect(() => {
    map.fitBounds(boundsOf(routes), { padding: 60, duration: 600 })
  }, [map, routes])

  // Highlight the selected route and draw it on top, without re-uploading any geometry.
  useEffect(() => {
    const isSelected: ExpressionSpecification = ['==', ['get', 'id'], selectedId]
    map.setPaintProperty(LINE_ID, 'line-color', ['case', isSelected, SELECTED_COLOR, OTHER_COLOR])
    map.setPaintProperty(LINE_ID, 'line-width', ['case', isSelected, 6, 4])
    map.setLayoutProperty(LINE_ID, 'line-sort-key', ['case', isSelected, 1, 0])
  }, [map, selectedId])

  // Click a route line to select it.
  useEffect(() => {
    const handleClick = (event: MapLayerMouseEvent) => {
      const id = event.features?.[0]?.properties.id
      if (typeof id === 'string') onSelect(id)
    }
    const setPointer = () => (map.getCanvas().style.cursor = 'pointer')
    const clearPointer = () => (map.getCanvas().style.cursor = '')
    map.on('click', LINE_ID, handleClick)
    map.on('mouseenter', LINE_ID, setPointer)
    map.on('mouseleave', LINE_ID, clearPointer)
    return () => {
      map.off('click', LINE_ID, handleClick)
      map.off('mouseenter', LINE_ID, setPointer)
      map.off('mouseleave', LINE_ID, clearPointer)
    }
  }, [map, onSelect])

  return null
}
