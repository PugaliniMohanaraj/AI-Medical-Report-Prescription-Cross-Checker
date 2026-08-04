import axios, { type AxiosProgressEvent } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
