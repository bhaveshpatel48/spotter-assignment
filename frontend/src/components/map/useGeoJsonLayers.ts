import type { FeatureCollection } from 'geojson'
import type { AddLayerObject, GeoJSONSource, Map } from 'maplibre-gl'
import { useEffect } from 'react'

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }

/** Adds a GeoJSON source and its layers once, keeps the source data in sync, and removes both
 * on unmount. Shared by every map layer component. `beforeId` places the layers under an
 * existing layer (e.g. under the map labels). */
export function useGeoJsonLayers(
  map: Map,
  sourceId: string,
  data: FeatureCollection,
  layers: AddLayerObject[],
  beforeId?: string,
) {
  useEffect(() => {
    map.addSource(sourceId, { type: 'geojson', data: EMPTY })
    layers.forEach((layer) => map.addLayer(layer, beforeId))
    return () => {
      if (map._removed) return
      layers.forEach((layer) => map.removeLayer(layer.id))
      map.removeSource(sourceId)
    }
    // The layers are fixed for the component's lifetime; only the data changes.
  }, [map, sourceId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    map.getSource<GeoJSONSource>(sourceId)?.setData(data)
  }, [map, sourceId, data])
}
