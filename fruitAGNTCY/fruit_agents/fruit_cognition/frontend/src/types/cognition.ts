/**
 * Mirrors the Pydantic models in cognition/schemas/* and the response
 * shapes in cognition/api/router.py. Keep in sync when those change.
 */

export type IntentStatus =
  | "draft"
  | "grounding"
  | "negotiating"
  | "approval_required"
  | "approved"
  | "rejected"
  | "committed"
  | "failed"

export interface IntentContract {
  intent_id: string
  goal: string
  fruit_type: string | null
  quantity_lb: number | null
  target_origin: string | null
  max_price_usd: number | null
  delivery_days: number | null
  hard_constraints: Record<string, unknown>
  soft_constraints: Record<string, unknown>
  human_approval_required_if: string[]
  status: IntentStatus
}

export interface IntentSummary {
  intent_id: string
  goal: string
  fruit_type: string | null
  quantity_lb: number | null
  status: IntentStatus
}

export interface Claim {
  claim_id: string
  intent_id: string
  agent_id: string
  claim_type: string
  subject: string
  value: Record<string, unknown>
  confidence: number
  evidence_refs: string[]
  created_at: string
}

export interface Belief {
  belief_id: string
  intent_id: string
  belief_type: string
  subject: string
  agent_id: string
  value: Record<string, unknown>
  confidence: number
  source_claim_ids: string[]
  created_at: string
}

export type ConflictSeverity = "low" | "medium" | "high" | "critical"

export interface Conflict {
  conflict_id: string
  intent_id: string
  conflict_type: string
  description: string
  involved_claims: string[]
  involved_beliefs: string[]
  severity: ConflictSeverity
  suggested_resolution: string | null
  created_at: string
}

export type WeatherRiskLevel = "low" | "medium" | "high" | "unknown"

export interface EvaluatedOption {
  intent_id: string
  supplier: string
  subject: string
  available_lb: number | null
  unit_price_usd: number | null
  fulfilled_lb: number | null
  total_price_usd: number | null
  within_budget: boolean | null
  cost_rank: number
  origin: string | null
  weather_risk_level: WeatherRiskLevel
  weather_score: number | null
  weather_reason: string | null
  allowed: boolean
  requires_human_approval: boolean
  violations: string[]
  rationale: string | null
}

export interface IntentStateResponse {
  intent: IntentContract
  claims: Claim[]
  beliefs: Belief[]
  conflicts: Conflict[]
  options: EvaluatedOption[]
}

export interface IntentListResponse {
  items: IntentSummary[]
}
