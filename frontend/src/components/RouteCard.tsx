import type { PlannedRoute, RiskLevel } from '../api/types'
import { formatDateTime, formatDuration, formatMiles } from '../lib/format'
import { RISK_LEVELS, RISK_STYLE } from '../lib/risk'
import styles from './RouteCard.module.css'

// The risk levels the ranking compares first, in ranking order (ADR-0007).
const RANKED_LEVELS: RiskLevel[] = ['NO_TRAVEL', 'SEVERE', 'HIGH']

interface Props {
  route: PlannedRoute
  /** Travel time of the fastest route in the plan, to show how much slower this one is. */
  fastestSeconds: number
  selected: boolean
  onSelect: (id: string) => void
}

export function RouteCard({ route, fastestSeconds, selected, onSelect }: Props) {
  const { summary } = route
  const miles = summary.miles_by_risk
  const hours = summary.travel_time_seconds / 3600
  const extraSeconds = summary.travel_time_seconds - fastestSeconds

  return (
    <button
      type="button"
      className={`${styles.card} ${selected ? styles.selected : ''}`}
      aria-pressed={selected}
      onClick={() => onSelect(route.id)}
    >
      <div className={styles.header}>
        <h3>Route {route.rank}</h3>
        {route.is_recommended && <span className={styles.tag}>Recommended</span>}
      </div>

      <p>
        {formatMiles(summary.distance_miles)} · {formatDuration(summary.travel_time_seconds)}
        {extraSeconds >= 60 && (
          <span className={styles.slower}> (+{formatDuration(extraSeconds)})</span>
        )}
        {' · '}avg {Math.round(summary.distance_miles / hours)} mph · arrives{' '}
        {formatDateTime(summary.arrival_time)}
      </p>

      {/* Miles at each risk level, as one stacked bar. */}
      <div className={styles.bar} aria-hidden>
        {RISK_LEVELS.map((level) => (
          <span
            key={level}
            style={{ flexGrow: miles[level], background: RISK_STYLE[level].color }}
          />
        ))}
      </div>

      {/* The values the ranking compares, in the same order, zeros included. */}
      <p className={styles.details}>
        {RANKED_LEVELS.map((level) => (
          <span key={level}>
            {RISK_STYLE[level].label} {formatMiles(miles[level])}
          </span>
        ))}
        <span>Avg risk {summary.average_risk.toFixed(2)} / 4</span>
      </p>

      <p className={route.is_recommended ? styles.reasonBest : styles.reason}>
        {route.is_recommended ? '✓ ' : ''}
        {route.ranking_reason}
      </p>
    </button>
  )
}
