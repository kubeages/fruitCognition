/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import React from "react"
import { Routes, Route, Navigate } from "react-router-dom"
import { RootPage, AdminPage, CognitionPage, DecisionsPage } from "@/pages"

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<RootPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="/cognition" element={<CognitionPage />} />
      <Route path="/decisions" element={<DecisionsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
