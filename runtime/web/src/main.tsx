import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App";
import UploadPage from "./pages/UploadPage";
import RunStatusPage from "./pages/RunStatusPage";
import ReportPage from "./pages/ReportPage";
import CatalogPage from "./pages/CatalogPage";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<App />}>
            <Route index element={<UploadPage />} />
            <Route path="/runs/:run_id" element={<RunStatusPage />} />
            <Route path="/runs/:run_id/report" element={<ReportPage />} />
            <Route path="/catalog" element={<CatalogPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
