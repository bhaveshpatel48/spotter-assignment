import type { RiskLevel } from '../api/types'

/** Ordered from lowest to highest; the index matches the backend's numeric risk (0-4). */
export const RISK_LEVELS: RiskLevel[] = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL']

/** The one place risk colours and labels are defined, so map, cards and badges always match. */
export const RISK_STYLE: Record<RiskLevel, { label: string; color: string }> = {
  LOW: { label: 'Low', color: '#2f9e44' },
  MODERATE: { label: 'Moderate', color: '#f2b705' },
  HIGH: { label: 'High', color: '#f76707' },
  SEVERE: { label: 'Severe', color: '#e03131' },
  NO_TRAVEL: { label: 'No Travel', color: '#862e9c' },
}
