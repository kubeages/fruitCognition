/**
 * Right-side drawer that opens when the user clicks any node in the
 * topology graph. Shows everything we know about that component —
 * description, role, identity verification, and external links to the
 * source code (GitHub) and the AGNTCY directory.
 *
 * Replaces the floating GitHub/AGNTCY/identity icons that used to sit
 * on each node card.
 */

import {
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material"
import CloseIcon from "@mui/icons-material/Close"
import OpenInNewIcon from "@mui/icons-material/OpenInNew"
import VerifiedIcon from "@mui/icons-material/Verified"
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline"
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty"

import type { CustomNodeData } from "./Elements/types"
import { SecurityClass } from "@/utils/SecurityClass"

export type InfoDrawerData =
  | (Pick<
      CustomNodeData,
      | "label1"
      | "label2"
      | "description"
      | "icon"
      | "githubLink"
      | "agentDirectoryLink"
      | "slug"
      | "farmName"
      | "agentCid"
      | "verificationStatus"
    > & { kind?: "node" })
  | {
      kind: "transport"
      label1: string
      label2?: string
      description?: string | string[]
      githubLink?: string
    }

export interface InfoDrawerProps {
  open: boolean
  onClose: () => void
  data: InfoDrawerData | null
  /** Called when the user clicks the Verification card; receives the slug
   *  (or label1) so the parent can open the existing identity modal. */
  onOpenIdentity?: (slug: string) => void
}

const verificationChip = (status: CustomNodeData["verificationStatus"]) => {
  if (status === "verified") {
    return (
      <Chip
        size="small"
        color="primary"
        icon={<VerifiedIcon fontSize="small" />}
        label="Verified"
      />
    )
  }
  if (status === "failed") {
    return (
      <Chip
        size="small"
        color="error"
        icon={<ErrorOutlineIcon fontSize="small" />}
        label="Verification failed"
      />
    )
  }
  if (status === "pending") {
    return (
      <Chip
        size="small"
        color="warning"
        icon={<HourglassEmptyIcon fontSize="small" />}
        label="Pending"
      />
    )
  }
  return null
}

const Paragraphs = ({
  description,
}: {
  description: string | string[] | undefined
}) => {
  if (!description) {
    return (
      <Typography variant="body2" color="text.secondary">
        No description provided yet.
      </Typography>
    )
  }
  const paragraphs = Array.isArray(description) ? description : [description]
  return (
    <Stack spacing={1}>
      {paragraphs.map((p, i) => (
        <Typography key={i} variant="body2" color="text.primary">
          {p}
        </Typography>
      ))}
    </Stack>
  )
}

const Field = ({
  label,
  value,
  monospace = false,
}: {
  label: string
  value: string | undefined | null
  monospace?: boolean
}) => {
  if (!value) return null
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          fontFamily: monospace ? "monospace" : undefined,
          wordBreak: "break-all",
        }}
      >
        {value}
      </Typography>
    </Box>
  )
}

const InfoDrawer = ({
  open,
  onClose,
  data,
  onOpenIdentity,
}: InfoDrawerProps) => {
  const isTransport = data?.kind === "transport"
  const node = !isTransport
    ? (data as Exclude<InfoDrawerData, { kind: "transport" }> | null)
    : null
  const transport = isTransport
    ? (data as Extract<InfoDrawerData, { kind: "transport" }>)
    : null

  const title = data?.label1 ?? ""
  const subtitle = isTransport ? transport?.label2 : node?.label2
  const description = data?.description
  const github = data?.githubLink
  const directory = !isTransport ? node?.agentDirectoryLink : undefined
  const slug = !isTransport ? (node?.slug ?? null) : null
  const farm = !isTransport ? (node?.farmName ?? null) : null
  const cid = !isTransport ? (node?.agentCid ?? null) : null
  const verification = !isTransport ? node?.verificationStatus : undefined

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: "100%", sm: 420 },
          bgcolor: "background.default",
          borderLeft: 1,
          borderColor: "divider",
        },
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", p: 2, gap: 1.5 }}>
        {!isTransport && node?.icon ? (
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: 1,
              bgcolor: "var(--node-icon-background, #fcefe1)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {node.icon}
          </Box>
        ) : (
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              bgcolor: "var(--node-icon-background, #fcefe1)",
              flexShrink: 0,
            }}
          />
        )}
        <Box sx={{ flexGrow: 1, minWidth: 0 }}>
          <Typography
            variant="h6"
            sx={{
              fontFamily: '"Merriweather", "Georgia", serif',
              fontWeight: 700,
              fontSize: "1.1rem",
              letterSpacing: -0.2,
              lineHeight: 1.2,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {title}
          </Typography>
          {subtitle ? (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          ) : null}
        </Box>
        <IconButton onClick={onClose} aria-label="Close" size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Box>

      <Divider />

      <Stack spacing={2.5} sx={{ p: 2.5, flexGrow: 1, overflowY: "auto" }}>
        <Box>
          <Typography variant="overline" color="text.secondary">
            About
          </Typography>
          <Paragraphs description={description} />
        </Box>

        {(slug || farm || cid) && (
          <>
            <Divider flexItem />
            <Stack spacing={1.25}>
              <Typography variant="overline" color="text.secondary">
                Identifiers
              </Typography>
              <Field label="Slug" value={slug} monospace />
              <Field label="Farm name" value={farm} />
              <Field label="Agent CID" value={cid} monospace />
            </Stack>
          </>
        )}

        {verification && (
          <>
            <Divider flexItem />
            <Box>
              <Typography variant="overline" color="text.secondary">
                Identity
              </Typography>
              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                sx={{ mt: 0.5 }}
              >
                {verificationChip(verification)}
                {verification === "verified" && onOpenIdentity ? (
                  <Button
                    size="small"
                    variant="outlined"
                    onClick={() => onOpenIdentity(slug ?? title)}
                  >
                    View badge & policies
                  </Button>
                ) : null}
              </Stack>
            </Box>
          </>
        )}

        {(github || directory) && (
          <>
            <Divider flexItem />
            <Stack spacing={1}>
              <Typography variant="overline" color="text.secondary">
                Resources
              </Typography>
              {github && SecurityClass.isSafeExternalUrl(github) ? (
                <Tooltip title={github}>
                  <Button
                    component="a"
                    href={github}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="outlined"
                    size="small"
                    startIcon={<OpenInNewIcon fontSize="small" />}
                    sx={{ justifyContent: "flex-start", textTransform: "none" }}
                  >
                    Source code on GitHub
                  </Button>
                </Tooltip>
              ) : null}
              {directory && SecurityClass.isSafeExternalUrl(directory) ? (
                <Tooltip title={directory}>
                  <Button
                    component="a"
                    href={directory}
                    target="_blank"
                    rel="noopener noreferrer"
                    variant="outlined"
                    size="small"
                    startIcon={<OpenInNewIcon fontSize="small" />}
                    sx={{ justifyContent: "flex-start", textTransform: "none" }}
                  >
                    AGNTCY Directory entry
                  </Button>
                </Tooltip>
              ) : null}
            </Stack>
          </>
        )}
      </Stack>
    </Drawer>
  )
}

export default InfoDrawer
