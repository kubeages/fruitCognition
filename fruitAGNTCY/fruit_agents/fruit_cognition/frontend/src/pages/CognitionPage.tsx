/**
 * Cognition view: read-only browser for intents, claims and beliefs
 * captured by the cognition fabric (in-memory or Postgres backend).
 */

import axios from "axios"
import { useCallback, useEffect, useMemo, useState } from "react"
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
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material"
import ArrowBackIcon from "@mui/icons-material/ArrowBack"
import RefreshIcon from "@mui/icons-material/Refresh"

import {
  fetchIntents,
  fetchIntentState,
  getCognitionApiUrl,
} from "@/utils/cognitionApi"
import type {
  Belief,
  Claim,
  IntentStateResponse,
  IntentSummary,
} from "@/types/cognition"

const statusColor = (
  status: string,
): "default" | "primary" | "success" | "warning" | "error" => {
  switch (status) {
    case "approved":
    case "committed":
      return "success"
    case "approval_required":
      return "warning"
    case "rejected":
    case "failed":
      return "error"
    case "grounding":
    case "negotiating":
      return "primary"
    default:
      return "default"
  }
}

const formatValue = (v: unknown): string => {
  if (v === null || v === undefined) return "—"
  if (typeof v === "number")
    return Number.isInteger(v) ? String(v) : v.toFixed(2)
  if (typeof v === "object") return JSON.stringify(v)
  return String(v)
}

const ClaimsTable = ({ claims }: { claims: Claim[] }) => {
  if (claims.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No claims have been recorded for this intent yet.
      </Typography>
    )
  }
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Subject</TableCell>
            <TableCell>Agent</TableCell>
            <TableCell>Value</TableCell>
            <TableCell align="right">Confidence</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {claims.map((c) => (
            <TableRow key={c.claim_id}>
              <TableCell>
                <Chip label={c.claim_type} size="small" />
              </TableCell>
              <TableCell>{c.subject}</TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {c.agent_id}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {formatValue(c.value)}
                </Typography>
              </TableCell>
              <TableCell align="right">{c.confidence.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const BeliefsTable = ({ beliefs }: { beliefs: Belief[] }) => {
  if (beliefs.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No beliefs derived yet — beliefs require at least one of inventory /
        price / quality / origin claims.
      </Typography>
    )
  }
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Subject</TableCell>
            <TableCell>Supplier</TableCell>
            <TableCell>Aggregated value</TableCell>
            <TableCell align="right">Confidence</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {beliefs.map((b) => (
            <TableRow key={b.belief_id}>
              <TableCell>
                <Chip label={b.belief_type} size="small" color="primary" />
              </TableCell>
              <TableCell>{b.subject}</TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {b.agent_id}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {formatValue(b.value)}
                </Typography>
              </TableCell>
              <TableCell align="right">{b.confidence.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const IntentDetail = ({ data }: { data: IntentStateResponse }) => {
  const intent = data.intent
  const fields: Array<[string, unknown]> = [
    ["Goal", intent.goal],
    ["Fruit", intent.fruit_type ?? "—"],
    ["Quantity (lb)", intent.quantity_lb ?? "—"],
    ["Max price (USD)", intent.max_price_usd ?? "—"],
    ["Delivery (days)", intent.delivery_days ?? "—"],
  ]
  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" alignItems="center" spacing={2} mb={1}>
          <Typography variant="h6" sx={{ fontFamily: "monospace" }}>
            {intent.intent_id}
          </Typography>
          <Chip
            label={intent.status}
            size="small"
            color={statusColor(intent.status)}
          />
        </Stack>
        <Stack
          direction="row"
          flexWrap="wrap"
          spacing={3}
          rowGap={1}
          divider={<Divider orientation="vertical" flexItem />}
        >
          {fields.map(([k, v]) => (
            <Box key={k}>
              <Typography variant="caption" color="text.secondary">
                {k}
              </Typography>
              <Typography variant="body2">{formatValue(v)}</Typography>
            </Box>
          ))}
        </Stack>
        {intent.human_approval_required_if.length > 0 ? (
          <Box mt={2}>
            <Typography variant="caption" color="text.secondary">
              Approval required if
            </Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" mt={0.5}>
              {intent.human_approval_required_if.map((tag) => (
                <Chip key={tag} label={tag} size="small" variant="outlined" />
              ))}
            </Stack>
          </Box>
        ) : null}
      </Paper>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Beliefs ({data.beliefs.length})
        </Typography>
        <BeliefsTable beliefs={data.beliefs} />
      </Box>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Claims ({data.claims.length})
        </Typography>
        <ClaimsTable claims={data.claims} />
      </Box>
    </Stack>
  )
}

const CognitionPage = () => {
  const [intents, setIntents] = useState<IntentSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<IntentStateResponse | null>(null)
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cognitionUrl = useMemo(getCognitionApiUrl, [])

  const reloadList = useCallback(async (signal?: AbortSignal) => {
    setLoadingList(true)
    setError(null)
    try {
      const data = await fetchIntents(signal)
      setIntents(data.items)
      // Auto-select the first intent if none chosen yet.
      if (data.items.length > 0 && selectedId === null) {
        setSelectedId(data.items[0].intent_id)
      }
    } catch (e: unknown) {
      if (axios.isCancel(e)) return
      setError(e instanceof Error ? e.message : "failed to load intents")
    } finally {
      setLoadingList(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const reloadDetail = useCallback(
    async (intentId: string, signal?: AbortSignal) => {
      setLoadingDetail(true)
      try {
        const data = await fetchIntentState(intentId, signal)
        setDetail(data)
      } catch (e: unknown) {
        if (axios.isCancel(e)) return
        setError(e instanceof Error ? e.message : "failed to load intent state")
      } finally {
        setLoadingDetail(false)
      }
    },
    [],
  )

  useEffect(() => {
    const ctrl = new AbortController()
    void reloadList(ctrl.signal)
    return () => ctrl.abort()
  }, [reloadList])

  useEffect(() => {
    if (!selectedId) return
    const ctrl = new AbortController()
    void reloadDetail(selectedId, ctrl.signal)
    return () => ctrl.abort()
  }, [selectedId, reloadDetail])

  const refreshAll = () => {
    void reloadList()
    if (selectedId) void reloadDetail(selectedId)
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
            Cognition
          </Typography>
          <Tooltip title={`Reading from ${cognitionUrl}/cognition`}>
            <Typography variant="caption" color="text.secondary" sx={{ mr: 2 }}>
              {cognitionUrl.replace(/^https?:\/\//, "")}
            </Typography>
          </Tooltip>
          <Button
            startIcon={<RefreshIcon />}
            onClick={refreshAll}
            size="small"
            variant="outlined"
          >
            Refresh
          </Button>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: 3 }}>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        ) : null}

        <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
          <Paper
            variant="outlined"
            sx={{ width: { xs: "100%", md: 320 }, flexShrink: 0 }}
          >
            <Box sx={{ p: 2, display: "flex", alignItems: "center" }}>
              <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                Intents ({intents.length})
              </Typography>
              {loadingList ? <CircularProgress size={16} /> : null}
            </Box>
            <Divider />
            {intents.length === 0 && !loadingList ? (
              <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                No intents captured yet. Send a chat prompt to generate one.
              </Typography>
            ) : (
              <List dense disablePadding>
                {intents.map((it) => (
                  <ListItemButton
                    key={it.intent_id}
                    selected={selectedId === it.intent_id}
                    onClick={() => setSelectedId(it.intent_id)}
                  >
                    <ListItemText
                      primary={it.fruit_type ?? it.goal}
                      secondary={`${it.quantity_lb ?? "?"} lb · ${it.intent_id.slice(0, 18)}…`}
                    />
                    <Chip
                      label={it.status}
                      size="small"
                      color={statusColor(it.status)}
                    />
                  </ListItemButton>
                ))}
              </List>
            )}
          </Paper>

          <Box sx={{ flexGrow: 1 }}>
            {selectedId === null ? (
              <Typography variant="body2" color="text.secondary">
                Pick an intent from the list to see its claims and beliefs.
              </Typography>
            ) : loadingDetail && detail === null ? (
              <CircularProgress />
            ) : detail ? (
              <IntentDetail data={detail} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                No data for this intent.
              </Typography>
            )}
          </Box>
        </Stack>
      </Container>
    </Box>
  )
}

export default CognitionPage
