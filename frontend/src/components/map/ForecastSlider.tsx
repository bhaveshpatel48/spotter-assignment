import { formatDateTime } from '../../lib/format'
import styles from './ForecastSlider.module.css'

const HOUR_MS = 60 * 60 * 1000

interface Props {
  startTime: string
  lastHour: number
  hour: number
  onChange: (hour: number) => void
}

export function ForecastSlider({ startTime, lastHour, hour, onChange }: Props) {
  const shownTime = new Date(new Date(startTime).getTime() + Math.round(hour) * HOUR_MS)

  return (
    <div className={styles.slider}>
      <label htmlFor="forecast-hour">
        Weather at <strong>{formatDateTime(shownTime.toISOString())}</strong>
        <span className={styles.offset}> · departure + {Math.round(hour)} h</span>
      </label>
      <input
        id="forecast-hour"
        type="range"
        min={0}
        max={lastHour}
        step={0.1}
        value={hour}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className={styles.scale}>
        <span>Departure</span>
        <span>+{lastHour + 1} h</span>
      </div>
    </div>
  )
}
