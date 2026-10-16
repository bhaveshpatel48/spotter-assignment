import { RISK_LEVELS } from '../../lib/risk'
import { RiskBadge } from '../RiskBadge'
import styles from './RiskLegend.module.css'

export function RiskLegend() {
  return (
    <div className={styles.legend}>
      {RISK_LEVELS.map((level) => (
        <RiskBadge key={level} level={level} />
      ))}
      <p className={styles.note}>
        <strong>Dots:</strong> risk when the truck gets there.
        <br />
        <strong>Shading:</strong> forecast at the slider time.
      </p>
    </div>
  )
}
