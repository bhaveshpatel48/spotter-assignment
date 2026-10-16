import { useState, type KeyboardEvent } from 'react'
import type { Place } from '../api/types'
import { usePlaceSearch } from '../hooks/usePlaceSearch'
import styles from './PlaceAutocomplete.module.css'

interface Props {
  id: string
  label: string
  value: Place | null
  onChange: (place: Place | null) => void
}

export function PlaceAutocomplete({ id, label, value, onChange }: Props) {
  const [text, setText] = useState(value?.label ?? '')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const results = usePlaceSearch(open ? text : '')
  const showList = open && results.length > 0

  function select(place: Place) {
    setText(place.label)
    setOpen(false)
    onChange(place)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!showList) return
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      const step = event.key === 'ArrowDown' ? 1 : -1
      setActive((current) => (current + step + results.length) % results.length)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      select(results[active])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className={styles.field}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        value={text}
        placeholder="City or address"
        autoComplete="off"
        role="combobox"
        aria-expanded={showList}
        aria-controls={`${id}-list`}
        onChange={(event) => {
          setText(event.target.value)
          setOpen(true)
          setActive(0)
          onChange(null)
        }}
        onKeyDown={handleKeyDown}
        onBlur={() => setOpen(false)}
      />
      {showList && (
        <ul id={`${id}-list`} role="listbox" className={styles.list}>
          {results.map((place, index) => (
            <li
              key={`${place.label}-${place.lat}-${place.lon}`}
              role="option"
              aria-selected={index === active}
              className={index === active ? styles.active : undefined}
              // mousedown fires before the input's blur, so the click is not lost.
              onMouseDown={(event) => {
                event.preventDefault()
                select(place)
              }}
            >
              {place.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
