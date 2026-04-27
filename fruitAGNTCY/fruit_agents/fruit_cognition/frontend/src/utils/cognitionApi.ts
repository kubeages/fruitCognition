/**
 * Thin fetch wrappers for the read-only /cognition/* endpoints.
 * Cognition routes are mounted on every supervisor; we hit the auction
 * supervisor by default since that's where claims are emitted today.
 */

import axios from "axios"
import { env } from "@/utils/env"
import type { IntentListResponse, IntentStateResponse } from "@/types/cognition"

const DEFAULT_COGNITION_API_URL = "http://127.0.0.1:8000"

export const getCognitionApiUrl = (): string =>
  env.get("VITE_COGNITION_API_URL") ||
  env.get("VITE_EXCHANGE_APP_API_URL") ||
  DEFAULT_COGNITION_API_URL

export const fetchIntents = async (
  signal?: AbortSignal,
): Promise<IntentListResponse> => {
  const { data } = await axios.get<IntentListResponse>(
    `${getCognitionApiUrl()}/cognition/intents`,
    { signal },
  )
  return data
}

export const fetchIntentState = async (
  intentId: string,
  signal?: AbortSignal,
): Promise<IntentStateResponse> => {
  const { data } = await axios.get<IntentStateResponse>(
    `${getCognitionApiUrl()}/cognition/intent/${encodeURIComponent(intentId)}/state`,
    { signal },
  )
  return data
}
