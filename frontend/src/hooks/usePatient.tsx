import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getErrorMessage } from "@/api/client";
import { getPatientOverview, processUploads } from "@/api/endpoints";
import type { PatientOverviewResponse, ProcessUploadsResponse } from "@/types/api";

interface PatientContextValue {
  overview: PatientOverviewResponse | null;
  loading: boolean;
  analyzing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  analyzeUploads: (fileIds?: string[]) => Promise<ProcessUploadsResponse>;
}

const PatientContext = createContext<PatientContextValue | null>(null);

const emptyOverview = (): PatientOverviewResponse => ({
  patient_id: "default-patient",
  allergies: [],
  visit_count: 0,
  visits: [],
  medicines: [],
  lab_visits: [],
  findings: [],
  has_uploads: false,
  has_extractions: false,
  disclaimer:
    "This tool supports clinical review only. It is not a diagnosis. Consult a doctor or pharmacist for high-risk or low-confidence findings.",
});

export function PatientProvider({ children }: { children: ReactNode }) {
  const [overview, setOverview] = useState<PatientOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPatientOverview();
      setOverview(data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
      setOverview((prev) => prev ?? emptyOverview());
    } finally {
      setLoading(false);
    }
  }, []);

  const analyzeUploads = useCallback(
    async (fileIds?: string[]) => {
      setAnalyzing(true);
      setError(null);
      try {
        const result = await processUploads({
          file_ids: fileIds,
          // Lightweight path: extraction + LLM only. RAG uses hash embeddings when enabled.
          ingest_rag: false,
        });
        await refresh();
        return result;
      } catch (err) {
        const message = getErrorMessage(err);
        setError(message);
        throw err;
      } finally {
        setAnalyzing(false);
      }
    },
    [refresh],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({
      overview,
      loading,
      analyzing,
      error,
      refresh,
      analyzeUploads,
    }),
    [overview, loading, analyzing, error, refresh, analyzeUploads],
  );

  return <PatientContext.Provider value={value}>{children}</PatientContext.Provider>;
}

export function usePatient() {
  const ctx = useContext(PatientContext);
  if (!ctx) {
    throw new Error("usePatient must be used within PatientProvider");
  }
  return ctx;
}
