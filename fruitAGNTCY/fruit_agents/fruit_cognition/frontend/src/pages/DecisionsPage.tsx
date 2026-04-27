/**
 * Decisions inbox: lists intents whose current decision requires human
 * approval, and lets the operator approve, reject, or request an
 * alternative. Designed per the M1 kickoff decision: chat stays
 * synchronous, decisions are reviewed here.
 */

import axios from "axios"
import { useCallback, useEffect, useRef, useState } from "react"
import { Link as RouterLink } from "react-router-dom"
import {
  Alert,
  AppBar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  IconButton,
  Paper,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material"
import ArrowBackIcon from "@mui/icons-material/ArrowBack"
import CheckCircleIcon from "@mui/icons-material/CheckCircle"
import CancelIcon from "@mui/icons-material/Cancel"
import RefreshIcon from "@mui/icons-material/Refresh"
import ChangeCircleIcon from "@mui/icons-material/ChangeCircle"

import {
  approveIntent,
  fetchApprovals,
  getCognitionApiUrl,
  rejectIntent,
  requestAlternativeIntent,
} from "@/utils/cognitionApi"
import type { ApprovalRequest, Plan } from "@/types/cognition"

type ActionFn = (intentId: string, note?: string) => Promise<unknown>

const PlanSummary = ({ plan }: { plan: Plan | null }) => {
  if (!plan) {
    return (
      <Typography variant="body2" color="text.secondary">
        No plan selected.
      </Typography>
    )
  }
  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="center" mb={0.5}>
        <Chip
          label={
            plan.plan_type === "single_supplier"
              ? "single supplier"
              : "split order"
          }
          size="small"
          color={plan.plan_type === "single_supplier" ? "default" : "primary"}
        />
        <Typography variant="body2">
          {plan.total_quantity_lb} lb ·{" "}
          {plan.total_price_usd === null
            ? "unpriced"
            : `$${plan.total_price_usd.toFixed(2)}`}
        </Typography>
      </Stack>
      <Stack direction="row" flexWrap="wrap" spacing={0.5}>
        {plan.suppliers.map((s) => (
          <Chip
            key={s.supplier}
            label={`${s.supplier} · ${s.quantity_lb} lb${s.unit_price_usd != null ? ` @ $${s.unit_price_usd}` : ""}`}
            size="small"
            variant="outlined"
            sx={{ fontFamily: "monospace" }}
          />
        ))}
      </Stack>
    </Box>
  )
}

const ApprovalCard = ({
  item,
  onAction,
  busy,
}: {
  item: ApprovalRequest
  onAction: (action: ActionFn, label: string) => Promise<void>
  busy: boolean
}) => {
  const intent = item.intent
  const decision = item.decision
  const fields: Array<[string, unknown]> = [
    ["Fruit", intent.fruit_type ?? "—"],
    ["Quantity", intent.quantity_lb ?? "—"],
    ["Max price", intent.max_price_usd ?? "—"],
    ["Delivery", intent.delivery_days ?? "—"],
  ]
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack direction="row" alignItems="center" spacing={1} mb={1}>
        <Typography
          variant="subtitle1"
          sx={{ fontFamily: "monospace", flexGrow: 1 }}
        >
          {intent.intent_id}
        </Typography>
        <Chip
          label={`mode: ${decision.mode}`}
          size="small"
          variant="outlined"
        />
        <Chip
          label={`confidence ${decision.confidence.toFixed(2)}`}
          size="small"
        />
      </Stack>

      <Stack direction="row" flexWrap="wrap" spacing={3} rowGap={1} mb={2}>
        {fields.map(([k, v]) => (
          <Box key={k}>
            <Typography variant="caption" color="text.secondary">
              {k}
            </Typography>
            <Typography variant="body2">
              {v == null ? "—" : String(v)}
            </Typography>
          </Box>
        ))}
      </Stack>

      <Box mb={2}>
        <Typography variant="caption" color="text.secondary">
          Proposed plan
        </Typography>
        <PlanSummary plan={decision.selected_plan} />
      </Box>

      <Box mb={2}>
        <Typography variant="caption" color="text.secondary">
          Why approval is needed
        </Typography>
        <Stack direction="row" spacing={0.5} flexWrap="wrap" mt={0.5}>
          {decision.approval_violations.length === 0 ? (
            <Typography variant="body2">—</Typography>
          ) : (
            decision.approval_violations.map((v) => (
              <Chip key={v} label={v} size="small" color="warning" />
            ))
          )}
        </Stack>
      </Box>

      <Typography variant="body2" sx={{ mb: 2 }}>
        {decision.rationale}
      </Typography>

      <Divider sx={{ my: 1 }} />

      <Stack direction="row" spacing={1}>
        <Button
          startIcon={<CheckCircleIcon />}
          color="success"
          variant="contained"
          size="small"
          disabled={busy}
          onClick={() => void onAction(approveIntent, "approve")}
        >
          Approve
        </Button>
        <Button
          startIcon={<CancelIcon />}
          color="error"
          variant="outlined"
          size="small"
          disabled={busy}
          onClick={() => void onAction(rejectIntent, "reject")}
        >
          Reject
        </Button>
        <Button
          startIcon={<ChangeCircleIcon />}
          color="primary"
          variant="outlined"
          size="small"
          disabled={busy}
          onClick={() =>
            void onAction(requestAlternativeIntent, "request_alternative")
          }
        >
          Request alternative
        </Button>
      </Stack>
    </Paper>
  )
}

const POLL_INTERVAL_MS = 3000

const DecisionsPage = () => {
  const [items, setItems] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  // Refs let the polling tick read latest state without re-creating the timer.
  const busyIdRef = useRef<string | null>(null)
  const inFlightRef = useRef<boolean>(false)

  const reload = useCallback(async (signal?: AbortSignal) => {
    if (inFlightRef.current) return
    inFlightRef.current = true
    setLoading(true)
    setError(null)
    try {
      setItems(await fetchApprovals(signal))
    } catch (e: unknown) {
      if (axios.isCancel(e)) return
      setError(e instanceof Error ? e.message : "failed to load approvals")
    } finally {
      setLoading(false)
      inFlightRef.current = false
    }
  }, [])

  useEffect(() => {
    busyIdRef.current = busyId
  }, [busyId])

  useEffect(() => {
    const ctrl = new AbortController()
    void reload(ctrl.signal)

    // Poll every POLL_INTERVAL_MS, skipping ticks when an action is mid-flight
    // so a user-driven approve/reject doesn't race with the background fetch.
    const id = window.setInterval(() => {
      if (busyIdRef.current !== null) return
      void reload()
    }, POLL_INTERVAL_MS)

    return () => {
      window.clearInterval(id)
      ctrl.abort()
    }
  }, [reload])

  const handleAction = async (
    intentId: string,
    fn: ActionFn,
    label: string,
  ) => {
    setBusyId(intentId)
    try {
      await fn(intentId)
      setInfo(`${label.replace("_", " ")}: ${intentId.slice(0, 24)}…`)
      await reload()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : `${label} failed`)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar>
          <IconButton
            component={RouterLink}
            to="/"
            edge="start"
            aria-label="back"
          >
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, ml: 1 }}>
            Decisions inbox
          </Typography>
          <Tooltip
            title={`Reading from ${getCognitionApiUrl()}/cognition/approvals`}
          >
            <Typography variant="caption" color="text.secondary" sx={{ mr: 2 }}>
              {getCognitionApiUrl().replace(/^https?:\/\//, "")} · polling{" "}
              {POLL_INTERVAL_MS / 1000}s
            </Typography>
          </Tooltip>
          <Button
            startIcon={<RefreshIcon />}
            size="small"
            variant="outlined"
            onClick={() => void reload()}
            disabled={loading}
          >
            Refresh
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ py: 3 }}>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        ) : null}
        {info ? (
          <Alert
            severity="success"
            sx={{ mb: 2 }}
            onClose={() => setInfo(null)}
          >
            {info}
          </Alert>
        ) : null}

        {loading && items.length === 0 ? (
          <CircularProgress />
        ) : items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            Nothing pending. When an intent's recommended plan triggers a policy
            in <code>human_approval_required_if</code>, it shows up here.
          </Typography>
        ) : (
          <Stack spacing={2}>
            {items.map((it) => (
              <ApprovalCard
                key={it.intent.intent_id}
                item={it}
                busy={busyId === it.intent.intent_id}
                onAction={(fn, label) =>
                  handleAction(it.intent.intent_id, fn, label)
                }
              />
            ))}
          </Stack>
        )}
      </Container>
    </Box>
  )
}

export default DecisionsPage
