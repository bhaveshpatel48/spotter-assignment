import { useCallback, useState } from 'react'
import type { Checkpoint, PlanRequest } from './api/types'
import styles from './App.module.css'
import { RankingExplainer } from './components/RankingExplainer'
import { RouteCard } from './components/RouteCard'
import { SearchForm } from './components/SearchForm'
import { StatusBanner } from './components/StatusBanner'
import { CheckpointsLayer } from './components/map/CheckpointsLayer'
import { MapView } from './components/map/MapView'
import { RiskLegend } from './components/map/RiskLegend'
import { RoutesLayer } from './components/map/RoutesLayer'
import { LAST_HOUR, WeatherLayer } from './components/map/WeatherLayer'
import { usePlanTrip } from './hooks/usePlanTrip'
import { hoursBetween } from './lib/format'

export default function App() {
  const { plan, error, loading, slow, submit } = usePlanTrip()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  // Hours after the departure hour shown on the forecast slider.
  const [hour, setHour] = useState(0)

  const selectedRoute =
    plan?.routes.find((route) => route.id === selectedId) ??
    plan?.routes.find((route) => route.id === plan.recommended_route_id)

  const fastestSeconds = Math.min(
    ...(plan?.routes.map((route) => route.summary.travel_time_seconds) ?? []),
  )

  function handleSubmit(request: PlanRequest) {
    setSelectedId(null) // a new plan starts on its recommended route
    setHour(0)
    submit(request)
  }

  // Clicking a checkpoint moves the slider to its ETA, so the dot and the shading show the
  // same moment. Stable between slider moves, so an open popup is not reset.
  const heatmapStart = plan?.heatmap.start_time
  const showCheckpointTime = useCallback(
    (checkpoint: Checkpoint) => {
      if (!heatmapStart) return
      setHour(Math.min(Math.max(hoursBetween(heatmapStart, checkpoint.eta), 0), LAST_HOUR))
    },
    [heatmapStart],
  )

  return (
    <div className={styles.app}>
      <aside className={styles.sidebar}>
        <h1>Weather-Aware Truck Routing</h1>
        <SearchForm loading={loading} onSubmit={handleSubmit} />
        <StatusBanner loading={loading} slow={slow} error={error} warnings={plan?.warnings ?? []} />
        {plan && (
          <section className={styles.routes} aria-label="Route options">
            {plan.routes.map((route) => (
              <RouteCard
                key={route.id}
                route={route}
                fastestSeconds={fastestSeconds}
                selected={route.id === selectedRoute?.id}
                onSelect={setSelectedId}
              />
            ))}
            <RankingExplainer />
          </section>
        )}
      </aside>

      <main className={styles.map}>
        <MapView>
          {(map) =>
            plan &&
            selectedRoute && (
              <>
                {/* Mount order is draw order: weather, then routes, then checkpoints on top. */}
                <WeatherLayer map={map} heatmap={plan.heatmap} hour={hour} onHourChange={setHour} />
                <RoutesLayer
                  map={map}
                  routes={plan.routes}
                  selectedId={selectedRoute.id}
                  onSelect={setSelectedId}
                />
                <CheckpointsLayer
                  map={map}
                  checkpoints={selectedRoute.checkpoints}
                  onSelect={showCheckpointTime}
                />
                <RiskLegend />
              </>
            )
          }
        </MapView>
      </main>
    </div>
  )
}
