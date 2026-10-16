export function formatMiles(miles: number): string {
  return `${Math.round(miles).toLocaleString()} mi`
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return hours ? `${hours} h ${minutes} m` : `${minutes} m`
}

/** A UTC timestamp from the API, shown in the user's local time, e.g. "Fri 3:40 PM". */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/** Whole and fractional hours from `startIso` to `endIso`. */
export function hoursBetween(startIso: string, endIso: string): number {
  return (new Date(endIso).getTime() - new Date(startIso).getTime()) / 3_600_000
}

/** Value for an <input type="datetime-local">, in the user's local time. */
export function toDateTimeInputValue(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}
