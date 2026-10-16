import { RISK_LEVELS, RISK_STYLE } from '../lib/risk'
import styles from './RankingExplainer.module.css'

/** How the backend ranks routes (ADR-0007), collapsed until the user opens it. */
export function RankingExplainer() {
  return (
    <details className={styles.explainer}>
      <summary>How routes are ranked</summary>

      <p>Routes are compared in this order. Each step only matters if the previous ones tie:</p>
      <ol>
        <li>Fewest {RISK_STYLE.NO_TRAVEL.label} miles</li>
        <li>Fewest {RISK_STYLE.SEVERE.label} miles</li>
        <li>Fewest {RISK_STYLE.HIGH.label} miles</li>
        <li>Lowest average risk</li>
        <li>Shortest travel time</li>
      </ol>

      <p>
        <strong>Average risk</strong> (0 to 4) is weighted by miles. Each level has a score:
      </p>
      <p className={styles.scores}>
        {RISK_LEVELS.map((level, score) => (
          <span key={level}>
            {RISK_STYLE[level].label} {score}
          </span>
        ))}
      </p>
      <p className={styles.formula}>(score × miles at each level) ÷ total miles</p>
      <p className={styles.example}>
        e.g. 75 mi Low + 25 mi Severe → (0 × 75 + 3 × 25) ÷ 100 = 0.75
      </p>
    </details>
  )
}
