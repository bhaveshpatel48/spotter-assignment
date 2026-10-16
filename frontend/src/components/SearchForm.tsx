import { useState, type FormEvent } from 'react'
import type { CheckpointSpacing, Place, PlanRequest } from '../api/types'
import { toDateTimeInputValue } from '../lib/format'
import { PlaceAutocomplete } from './PlaceAutocomplete'
import styles from './SearchForm.module.css'

const SPACINGS: CheckpointSpacing[] = [10, 25, 50]
const MAX_LOAD_LB = 80_000
// A ready-to-run example: I-80 through Wyoming is known for high-wind truck closures.
const EXAMPLE_ORIGIN: Place = { label: 'Denver, CO', lat: 39.738, lon: -104.985 }
const EXAMPLE_DESTINATION: Place = { label: 'Salt Lake City, UT', lat: 40.758, lon: -111.888 }

interface Props {
  loading: boolean
  onSubmit: (request: PlanRequest) => void
}

export function SearchForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(EXAMPLE_ORIGIN)
  const [destination, setDestination] = useState<Place | null>(EXAMPLE_DESTINATION)
  const [departure, setDeparture] = useState(() =>
    toDateTimeInputValue(new Date(Date.now() + 60 * 60 * 1000)),
  )
  const [loadLb, setLoadLb] = useState('42000')
  const [spacing, setSpacing] = useState<CheckpointSpacing>(25)
  const [restBreaks, setRestBreaks] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const load = Number(loadLb)
    if (!origin || !destination) {
      return setFormError('Choose an origin and a destination from the suggestions.')
    }
    if (!Number.isInteger(load) || load < 1 || load > MAX_LOAD_LB) {
      return setFormError(`Load must be a whole number from 1 to ${MAX_LOAD_LB.toLocaleString()} lb.`)
    }
    setFormError(null)
    onSubmit({
      origin,
      destination,
      departure_time: new Date(departure).toISOString(),
      load_weight_lb: load,
      checkpoint_spacing_miles: spacing,
      include_rest_breaks: restBreaks,
    })
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <PlaceAutocomplete id="origin" label="Origin" value={origin} onChange={setOrigin} />
      <PlaceAutocomplete
        id="destination"
        label="Destination"
        value={destination}
        onChange={setDestination}
      />

      <div className={styles.row}>
        <div>
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            onChange={(event) => setDeparture(event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="load">Load (lb)</label>
          <input
            id="load"
            type="number"
            min={1}
            max={MAX_LOAD_LB}
            step={1}
            value={loadLb}
            onChange={(event) => setLoadLb(event.target.value)}
            required
          />
        </div>
      </div>

      <fieldset className={styles.spacing}>
        <legend>Weather checkpoint every</legend>
        {SPACINGS.map((miles) => (
          <label key={miles} className={spacing === miles ? styles.selected : undefined}>
            <input
              type="radio"
              name="spacing"
              checked={spacing === miles}
              onChange={() => setSpacing(miles)}
            />
            {miles} mi
          </label>
        ))}
      </fieldset>

      <label className={styles.checkbox}>
        <input
          type="checkbox"
          checked={restBreaks}
          onChange={(event) => setRestBreaks(event.target.checked)}
        />
        Include driver rest breaks
      </label>

      {formError && <p className={styles.error}>{formError}</p>}

      <button type="submit" className={styles.submit} disabled={loading}>
        {loading ? 'Planning…' : 'Find routes'}
      </button>
    </form>
  )
}
