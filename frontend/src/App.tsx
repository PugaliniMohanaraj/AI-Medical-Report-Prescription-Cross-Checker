import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { AiChatPage } from "@/pages/AiChatPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LabTrendsPage } from "@/pages/LabTrendsPage";
import { MedicinesPage } from "@/pages/MedicinesPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { TimelinePage } from "@/pages/TimelinePage";
import { UploadPage } from "@/pages/UploadPage";
import { WarningsPage } from "@/pages/WarningsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/timeline" element={<TimelinePage />} />
        <Route path="/medicines" element={<MedicinesPage />} />
        <Route path="/labs" element={<LabTrendsPage />} />
        <Route path="/warnings" element={<WarningsPage />} />
        <Route path="/chat" element={<AiChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/uploads" element={<UploadPage />} />
        {/* Legacy redirects */}
        <Route path="/upload" element={<Navigate to="/uploads" replace />} />
        <Route path="/analysis" element={<Navigate to="/warnings" replace />} />
        <Route path="/ask" element={<Navigate to="/chat" replace />} />
      </Route>
    </Routes>
  );
}
