import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Place } from '../api/types'
import { useDebouncedValue } from './useDebouncedValue'

const DEBOUNCE_MS = 300
const MIN_QUERY_LENGTH = 3

/** Place suggestions for `query`, fetched 300 ms after typing stops (ADR-0004). */
export function usePlaceSearch(query: string): Place[] {
  const debounced = useDebouncedValue(query.trim(), DEBOUNCE_MS)
  const [results, setResults] = useState<{ query: string; places: Place[] }>({
    query: '',
    places: [],
  })
  const tooShort = debounced.length < MIN_QUERY_LENGTH

  useEffect(() => {
    if (tooShort) return
    const controller = new AbortController()
    api
      .geocode(debounced, controller.signal)
      .then((places) => setResults({ query: debounced, places }))
      // Suggestions are optional; a failed lookup simply shows none.
      .catch(() => undefined)
    return () => controller.abort()
  }, [debounced, tooShort])

  return !tooShort && results.query === debounced ? results.places : []
}
