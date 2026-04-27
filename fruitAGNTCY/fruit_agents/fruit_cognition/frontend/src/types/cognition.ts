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

export interface IntentStateResponse {
  intent: IntentContract
  claims: Claim[]
  beliefs: Belief[]
}

export interface IntentListResponse {
  items: IntentSummary[]
}
