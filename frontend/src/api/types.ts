// Mirrors the API contract in docs/ARCHITECTURE.md §3.

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'NO_TRAVEL'

export type CheckpointSpacing = 10 | 25 | 50

export interface Place {
  label: string
  lat: number
  lon: number
}

export interface PlanRequest {
  origin: Place
  destination: Place
  departure_time: string
  load_weight_lb: number
  checkpoint_spacing_miles: CheckpointSpacing
  include_rest_breaks: boolean
}

export interface Weather {
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
}

export interface Checkpoint {
  index: number
  mile: number
  lat: number
  lon: number
  eta: string
  weather: Weather
  risk_level: RiskLevel
  risk_reasons: string[]
}

export interface RouteSummary {
  distance_miles: number
  travel_time_seconds: number
  departure_time: string
  arrival_time: string
  miles_by_risk: Record<RiskLevel, number>
  average_risk: number
}

export interface PlannedRoute {
  id: string
  rank: number
  is_recommended: boolean
  summary: RouteSummary
  geometry: [lon: number, lat: number][]
  checkpoints: Checkpoint[]
}

export interface HeatmapPoint {
  lat: number
  lon: number
  /** Risk level 0 (Low) to 4 (No Travel) for each hour after `start_time`. */
  risk: number[]
}

export interface Heatmap {
  start_time: string
  hours: number
  cell_size_deg: number
  points: HeatmapPoint[]
}

export interface PlanWarning {
  code: string
  message: string
}

export interface TripPlan {
  generated_at: string
  recommended_route_id: string
  warnings: PlanWarning[]
  routes: PlannedRoute[]
  heatmap: Heatmap
}
