import { useCallback, useState } from 'react'
import { ApiError, api } from '../api/client'
import type { PlanRequest, TripPlan } from '../api/types'

// The free backend sleeps when idle; a request this slow is probably waking it up.
const SLOW_AFTER_MS = 8_000

export function usePlanTrip() {
  const [plan, setPlan] = useState<TripPlan | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(false)
  const [slow, setSlow] = useState(false)

  const submit = useCallback(async (request: PlanRequest) => {
    setLoading(true)
    setError(null)
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS)
    try {
      setPlan(await api.plan(request))
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught
          : new ApiError('UNKNOWN_ERROR', 'Something went wrong. Please try again.', null),
      )
    } finally {
      clearTimeout(timer)
      setLoading(false)
      setSlow(false)
    }
  }, [])

  return { plan, error, loading, slow, submit }
}
