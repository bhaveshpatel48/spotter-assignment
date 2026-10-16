import type { RiskLevel } from '../api/types'
import { RISK_STYLE } from '../lib/risk'
import styles from './RiskBadge.module.css'

/** Risk shown as colour plus text, so it stays readable without colour. */
export function RiskBadge({ level }: { level: RiskLevel }) {
  const { label, color } = RISK_STYLE[level]
  return (
    <span className={styles.badge}>
      <span className={styles.dot} style={{ background: color }} />
      {label}
    </span>
  )
}
