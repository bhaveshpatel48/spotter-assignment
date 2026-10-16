import type { Place, PlanRequest, TripPlan } from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

/** Every failed request becomes an ApiError, using the backend's error format when present. */
export class ApiError extends Error {
  readonly code: string
  readonly requestId: string | null

  constructor(code: string, message: string, requestId: string | null) {
    super(message)
    this.code = code
    this.requestId = requestId
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init.headers },
    })
  } catch (error) {
    if (init.signal?.aborted) throw error
    throw new ApiError('NETWORK_ERROR', 'Could not reach the server. Please try again.', null)
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = body?.error
    throw new ApiError(
      error?.code ?? 'HTTP_ERROR',
      error?.message ?? `Request failed with status ${response.status}.`,
      error?.request_id ?? response.headers.get('X-Request-ID'),
    )
  }
  return body as T
}

export const api = {
  geocode: (query: string, signal?: AbortSignal) =>
    request<{ results: Place[] }>(`/api/geocode?q=${encodeURIComponent(query)}`, { signal }).then(
      (body) => body.results,
    ),

  plan: (body: PlanRequest) =>
    request<TripPlan>('/api/plan', { method: 'POST', body: JSON.stringify(body) }),
}
