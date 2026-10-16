import type { PlannedRoute } from '../api/types'
import { formatDateTime, formatDuration, formatMiles } from '../lib/format'
import { RISK_LEVELS, RISK_STYLE } from '../lib/risk'
import styles from './RouteCard.module.css'

interface Props {
  route: PlannedRoute
  selected: boolean
  onSelect: (id: string) => void
}

export function RouteCard({ route, selected, onSelect }: Props) {
  const { summary } = route
  const miles = summary.miles_by_risk

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
        {formatMiles(summary.distance_miles)} · {formatDuration(summary.travel_time_seconds)} ·
        arrives {formatDateTime(summary.arrival_time)}
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

      <p className={styles.details}>
        {RISK_LEVELS.filter((level) => level !== 'LOW' && miles[level] > 0).map((level) => (
          <span key={level}>
            {RISK_STYLE[level].label} {formatMiles(miles[level])}
          </span>
        ))}
        <span>Avg risk {summary.average_risk.toFixed(2)}</span>
      </p>
    </button>
  )
}
