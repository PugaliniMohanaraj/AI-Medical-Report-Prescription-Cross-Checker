import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { PatientProvider } from "@/hooks/usePatient";
import { ThemeProvider } from "@/theme/ThemeProvider";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <PatientProvider>
          <App />
        </PatientProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
);
