import { Map, NavigationControl, setWorkerUrl } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import styles from './MapView.module.css'

const MAP_KEY = import.meta.env.VITE_TOMTOM_MAP_KEY
// TomTom Orbis grey "mono light" style, so the coloured routes and weather stand out.
const STYLE_URL = `https://api.tomtom.com/maps/orbis/assets/styles/0.*/style.json?apiVersion=1&map=basic_mono-light&key=${MAP_KEY}`
const CONTIGUOUS_US_CENTER: [number, number] = [-98.5, 39.5]

// MapLibre finds its worker next to its own file, which bundling moves; point it at the file.
setWorkerUrl(workerUrl)

/** Creates the map once and renders `children(map)` (the data layers) after it has loaded. */
export function MapView({ children }: { children: (map: Map) => ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<Map | null>(null)

  useEffect(() => {
    const instance = new Map({
      container: containerRef.current!,
      style: STYLE_URL,
      center: CONTIGUOUS_US_CENTER,
      zoom: 3.4,
      attributionControl: { compact: true, customAttribution: 'Weather © Open-Meteo' },
    })
    instance.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    instance.on('load', () => setMap(instance))
    return () => {
      setMap(null)
      instance.remove()
    }
  }, [])

  return (
    <div className={styles.wrapper}>
      <div ref={containerRef} className={styles.map} />
      {map && children(map)}
    </div>
  )
}
