/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React, { useRef } from "react"
import { Handle, Position } from "@xyflow/react"
import identityBadgeIcon from "@/assets/identity_badge.svg"
import { CustomNodeData, ExtraHandle } from "./types"

const POSITION_MAP: Record<ExtraHandle["position"], Position> = {
  top: Position.Top,
  bottom: Position.Bottom,
  left: Position.Left,
  right: Position.Right,
}

interface CustomNodeProps {
  data: CustomNodeData
  onOpenOasfModal?: (
    nodeData: CustomNodeData,
    position: { x: number; y: number },
  ) => void
}

const CustomNode: React.FC<CustomNodeProps> = ({ data }) => {
  const nodeRef = useRef<HTMLDivElement>(null)

  const handleNodeClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (typeof data.onOpenInfoDrawer === "function") {
      data.onOpenInfoDrawer(data)
    }
  }

  const activeClasses = data.active
    ? "bg-node-background-active outline outline-2 outline-accent-border shadow-[var(--shadow-default)_0px_6px_8px]"
    : data.selected
      ? "bg-node-background outline outline-2 outline-accent-primary shadow-[var(--shadow-default)_0px_6px_8px]"
      : "bg-node-background"

  return (
    <>
      <div
        ref={nodeRef}
        onClick={handleNodeClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            handleNodeClick(e as unknown as React.MouseEvent)
          }
        }}
        className={`order-0 relative flex h-[91px] w-[193px] flex-none grow-0 cursor-pointer flex-col items-start justify-start gap-2 rounded-lg p-4 ${activeClasses} hover:bg-node-background-hover hover:shadow-[var(--shadow-default)_0px_6px_8px] hover:outline hover:outline-2 hover:outline-accent-border`}
      >
        <div className="flex h-5 w-5 flex-shrink-0 items-center justify-center gap-2.5 rounded bg-node-icon-background py-1 opacity-100">
          <div className="flex h-4 w-4 items-center justify-center opacity-100">
            {data.icon}
          </div>
        </div>

        <div
          className="order-0 flex h-5 flex-none grow-0 flex-row items-center gap-1 self-stretch p-0"
          style={{
            width: data.verificationStatus === "verified" ? "160px" : "162px",
          }}
        >
          <span className="order-0 flex h-5 flex-none grow-0 items-center overflow-hidden text-ellipsis whitespace-nowrap font-inter text-sm font-normal leading-5 tracking-normal text-node-text-primary opacity-100">
            {data.label1}
          </span>
          {data.verificationStatus === "verified" && (
            <img
              src={identityBadgeIcon}
              alt="Verified"
              className="order-1 h-4 w-4 flex-none grow-0"
            />
          )}
        </div>

        <div
          className="order-1 h-4 flex-none flex-grow-0 self-stretch overflow-hidden text-ellipsis whitespace-nowrap font-inter text-xs font-light leading-4 text-node-text-secondary"
          style={{
            width: "162px",
          }}
        >
          {data.label2}
        </div>

        {(data.handles === "all" || data.handles === "target") && (
          <Handle
            type="target"
            position={Position.Top}
            id="target"
            className="h-px w-px border border-gray-600 bg-node-data-background"
          />
        )}
        {(data.handles === "all" || data.handles === "source") && (
          <Handle
            type="source"
            position={Position.Bottom}
            id="source"
            className="h-px w-px border border-gray-600 bg-node-data-background"
          />
        )}
        {data.extraHandles?.map((eh) => (
          <Handle
            key={eh.id}
            type={eh.type}
            position={POSITION_MAP[eh.position]}
            id={eh.id}
            className="h-px w-px border border-gray-600 bg-node-data-background"
          />
        ))}
      </div>
    </>
  )
}

export default CustomNode
