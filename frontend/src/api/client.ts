import axios, { type AxiosProgressEvent } from "axios";

const fallbackBase = "http://localhost:8000/api/v1";
const baseURL = import.meta.env.VITE_API_BASE_URL ?? fallbackBase;

if (import.meta.env.PROD && !import.meta.env.VITE_API_BASE_URL) {
  console.warn(
    "[MedCross] VITE_API_BASE_URL is not set. Production builds will call localhost and fail. Set it in Vercel to your Render API …/api/v1 and rebuild.",
  );
}

export const apiClient = axios.create({
  baseURL,
  timeout: 300_000,
});

apiClient.defaults.headers.common["Accept"] = "application/json";

export type UploadProgressHandler = (event: AxiosProgressEvent) => void;

export function getErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : "Unexpected error";
  }

  const detail = error.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (detail && typeof detail === "object" && Array.isArray(detail.errors)) {
    return [detail.message, ...detail.errors].filter(Boolean).join("\n");
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === "object" && item?.msg ? item.msg : String(item)))
      .join("\n");
  }
  return error.message || "Request failed";
}
