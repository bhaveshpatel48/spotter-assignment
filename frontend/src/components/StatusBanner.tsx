import type { ApiError } from '../api/client'
import type { PlanWarning } from '../api/types'
import styles from './StatusBanner.module.css'

interface Props {
  loading: boolean
  slow: boolean
  error: ApiError | null
  warnings: PlanWarning[]
}

export function StatusBanner({ loading, slow, error, warnings }: Props) {
  if (loading) {
    return (
      <p className={styles.info} role="status">
        {slow
          ? 'Waking up the server… the first request after a quiet period can take up to a minute.'
          : 'Planning routes and checking the weather…'}
      </p>
    )
  }
  if (error) {
    return (
      <div className={styles.error} role="alert">
        <p>{error.message}</p>
        {error.requestId && <p className={styles.requestId}>Request ID: {error.requestId}</p>}
      </div>
    )
  }
  return warnings.map((warning) => (
    <p key={warning.code} className={styles.warning} role="status">
      {warning.message}
    </p>
  ))
}
