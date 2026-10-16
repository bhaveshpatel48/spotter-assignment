import { Popup, type AddLayerObject, type Map, type MapLayerMouseEvent } from 'maplibre-gl'
import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import type { Checkpoint } from '../../api/types'
import { formatDateTime } from '../../lib/format'
import { checkpointsToGeoJson } from '../../lib/mapData'
import { RiskBadge } from '../RiskBadge'
import styles from './CheckpointsLayer.module.css'
import { useGeoJsonLayers } from './useGeoJsonLayers'

const SOURCE_ID = 'checkpoints'
const CIRCLE_ID = 'checkpoints-circle'

const LAYERS: AddLayerObject[] = [
  {
    id: CIRCLE_ID,
    type: 'circle',
    source: SOURCE_ID,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 10, 8],
      'circle-color': ['get', 'color'],
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 1.5,
    },
  },
]

interface Props {
  map: Map
  checkpoints: Checkpoint[]
  onSelect: (checkpoint: Checkpoint) => void
}

/** The selected route's checkpoints, coloured by risk. Clicking one opens its details. */
export function CheckpointsLayer({ map, checkpoints, onSelect }: Props) {
  const data = useMemo(() => checkpointsToGeoJson(checkpoints), [checkpoints])
  useGeoJsonLayers(map, SOURCE_ID, data, LAYERS)

  const [selected, setSelected] = useState<Checkpoint | null>(null)
  // React renders the popup content into our own element, so it can reuse RiskBadge and
  // formatting. (The popup's own element only exists once it is on the map.)
  const [content] = useState(() => document.createElement('div'))
  const [popup] = useState(() => new Popup({ maxWidth: '280px' }))

  useEffect(() => {
    const handleClick = (event: MapLayerMouseEvent) => {
      const index = event.features?.[0]?.properties.index
      const checkpoint = checkpoints.find((candidate) => candidate.index === index)
      if (!checkpoint) return
      setSelected(checkpoint)
      onSelect(checkpoint)
    }
    const setPointer = () => (map.getCanvas().style.cursor = 'pointer')
    const clearPointer = () => (map.getCanvas().style.cursor = '')
    map.on('click', CIRCLE_ID, handleClick)
    map.on('mouseenter', CIRCLE_ID, setPointer)
    map.on('mouseleave', CIRCLE_ID, clearPointer)
    return () => {
      map.off('click', CIRCLE_ID, handleClick)
      map.off('mouseenter', CIRCLE_ID, setPointer)
      map.off('mouseleave', CIRCLE_ID, clearPointer)
      setSelected(null)
    }
  }, [map, checkpoints, onSelect])

  useEffect(() => {
    if (!selected) return
    const handleClose = () => setSelected(null)
    popup
      .setLngLat([selected.lon, selected.lat])
      .setDOMContent(content)
      .addTo(map)
      .on('close', handleClose)
    return () => {
      popup.off('close', handleClose)
      popup.remove()
    }
  }, [map, popup, content, selected])

  return selected && createPortal(<CheckpointDetails checkpoint={selected} />, content)
}

function CheckpointDetails({ checkpoint }: { checkpoint: Checkpoint }) {
  const { weather } = checkpoint
  return (
    <div className={styles.details}>
      <div className={styles.header}>
        <strong>Mile {Math.round(checkpoint.mile)}</strong>
        <RiskBadge level={checkpoint.risk_level} />
      </div>
      <p>ETA {formatDateTime(checkpoint.eta)}</p>
      <dl>
        <dt>Wind</dt>
        <dd>
          {weather.wind_mph.toFixed(0)} mph (gusts {weather.gust_mph.toFixed(0)})
        </dd>
        <dt>Rain</dt>
        <dd>{weather.rain_in_hr.toFixed(2)} in/hr</dd>
        <dt>Snow</dt>
        <dd>{weather.snow_in_hr.toFixed(2)} in/hr</dd>
      </dl>
      {checkpoint.risk_reasons.length > 0 && (
        <ul>
          {checkpoint.risk_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
