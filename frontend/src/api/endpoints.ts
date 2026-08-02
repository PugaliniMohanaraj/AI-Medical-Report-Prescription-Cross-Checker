import { apiClient, type UploadProgressHandler } from "@/api/client";
import type {
  HealthResponse,
  LabTrendRequest,
  LabTrendResponse,
  PrescriptionAnalysisRequest,
  PrescriptionAnalysisResponse,
  RagIngestRequest,
  RagIngestResponse,
  RagQueryRequest,
  RagQueryResponse,
  UploadListResponse,
  UploadResponse,
  UploadedFileInfo,
} from "@/types/api";

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/health");
  return data;
}

export async function uploadPdfs(
  files: File[],
  onUploadProgress?: UploadProgressHandler,
): Promise<UploadResponse> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));

  const { data } = await apiClient.post<UploadResponse>("/uploads", form, {
    onUploadProgress,
  });
  return data;
}

export async function listUploads(): Promise<UploadListResponse> {
  const { data } = await apiClient.get<UploadListResponse>("/uploads");
  return data;
}

export async function getUpload(fileId: string): Promise<UploadedFileInfo> {
  const { data } = await apiClient.get<UploadedFileInfo>(`/uploads/${fileId}`);
  return data;
}

export async function deleteUpload(fileId: string): Promise<void> {
  await apiClient.delete(`/uploads/${fileId}`);
}

export async function analyzePrescription(
  payload: PrescriptionAnalysisRequest,
): Promise<PrescriptionAnalysisResponse> {
  const { data } = await apiClient.post<PrescriptionAnalysisResponse>(
    "/analysis/prescription",
    payload,
  );
  return data;
}

export async function analyzeLabTrends(payload: LabTrendRequest): Promise<LabTrendResponse> {
  const { data } = await apiClient.post<LabTrendResponse>("/analysis/labs", payload);
  return data;
}

export async function ingestRagDocuments(payload: RagIngestRequest): Promise<RagIngestResponse> {
  const { data } = await apiClient.post<RagIngestResponse>("/rag/ingest", payload);
  return data;
}

export async function queryRag(payload: RagQueryRequest): Promise<RagQueryResponse> {
  const { data } = await apiClient.post<RagQueryResponse>("/rag/query", payload);
  return data;
}
