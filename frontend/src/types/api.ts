export interface ConfidenceScore {
  score: number;
  rationale?: string | null;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  environment: string;
  llm_provider: string;
}

export interface UploadedFileInfo {
  file_id: string;
  filename: string;
  size_bytes: number;
  content_type: string;
  uploaded_at: string;
  checksum_sha256?: string | null;
}

export interface UploadResponse {
  files: UploadedFileInfo[];
  message: string;
  count: number;
}

export interface UploadListResponse {
  files: UploadedFileInfo[];
  count: number;
}

export interface UploadValidationErrorBody {
  message: string;
  errors: string[];
}

export interface RagQueryRequest {
  question: string;
  patient_id?: string | null;
  session_id?: string | null;
  top_k?: number;
}

export interface RagSource {
  document_id: string;
  excerpt: string;
  score?: number | null;
  title?: string | null;
  source?: string | null;
  metadata?: Record<string, unknown>;
}

export interface RagQueryResponse {
  answer: string;
  confidence: ConfidenceScore;
  sources: RagSource[];
  llm_provider?: string | null;
  retrieval_backend?: string | null;
}

export interface RagDocumentInput {
  content: string;
  document_id?: string | null;
  title?: string | null;
  source?: string | null;
  patient_id?: string | null;
  visit_date?: string | null;
  file_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface RagIngestRequest {
  documents?: RagDocumentInput[];
  file_ids?: string[];
  patient_id?: string | null;
}

export interface RagIngestResponse {
  documents_ingested: number;
  chunks_indexed: number;
  backend: string;
  embedding_backend: string;
  message: string;
}

export interface ConflictFinding {
  type: string;
  severity: "Low" | "Medium" | "High" | string;
  title: string;
  explanation: string;
  description?: string | null;
  related_medicines: string[];
  related_allergies?: string[];
  confidence: ConfidenceScore;
}

export interface MedicineInput {
  name?: string | null;
  dosage?: string | null;
  frequency?: string | null;
  duration?: string | null;
}

export interface PrescriptionAnalysisRequest {
  medicines: MedicineInput[];
  allergies?: string[];
}

export interface SeveritySummary {
  low: number;
  medium: number;
  high: number;
  total: number;
}

export interface PrescriptionAnalysisResponse {
  findings: ConflictFinding[];
  summary: SeveritySummary;
  medicines_analyzed: number;
  allergies_considered: number;
}

export interface LabResultInput {
  test_name?: string | null;
  value?: string | null;
  unit?: string | null;
  reference_range?: string | null;
  status?: string | null;
}

export interface LabVisitInput {
  visit_id?: string | null;
  visit_date: string;
  labs: LabResultInput[];
}

export interface LabTrendRequest {
  patient_id?: string | null;
  visits: LabVisitInput[];
  include_ai_explanation?: boolean;
}

export interface LabDataPoint {
  visit_id?: string | null;
  visit_date: string;
  value: number;
  unit?: string | null;
  status: string;
  is_abnormal: boolean;
}

export interface LabTrendSeries {
  test_name: string;
  unit?: string | null;
  reference_range?: string | null;
  reference_low?: number | null;
  reference_high?: number | null;
  points: LabDataPoint[];
  direction: string;
  percent_change?: number | null;
  is_abnormal_trend: boolean;
  severity: string;
  trend_summary: string;
}

export interface LabChartPoint {
  date: string;
  value: number;
  abnormal: boolean;
  status?: string;
  visit_id?: string | null;
}

export interface LabChartSeries {
  test_name: string;
  unit?: string | null;
  reference_low?: number | null;
  reference_high?: number | null;
  is_abnormal_trend: boolean;
  severity: string;
  data: LabChartPoint[];
}

export interface LabTrendResponse {
  patient_id?: string | null;
  visit_count: number;
  series: LabTrendSeries[];
  abnormal_trends: LabTrendSeries[];
  charts: LabChartSeries[];
  ai_explanation?: string | null;
  confidence: ConfidenceScore;
  llm_provider?: string | null;
}
