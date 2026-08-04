import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getErrorMessage } from "@/api/client";
import { deleteUpload, listUploads, uploadFiles } from "@/api/endpoints";
import { FileDropzone } from "@/components/FileDropzone";
import { MedicalDisclaimer } from "@/components/MedicalDisclaimer";
import { QueuedFileList, StoredUploadsList } from "@/components/UploadFileLists";
import { UploadProgressBar } from "@/components/UploadProgressBar";
import { PageHeader } from "@/components/ui/PageHeader";
import { usePatient } from "@/hooks/usePatient";
import type { ProcessUploadsResponse, UploadedFileInfo } from "@/types/api";
import {
  MAX_UPLOAD_FILES,
  MAX_UPLOAD_SIZE_MB,
  validateUploadFiles,
} from "@/utils/upload";

export function UploadPage() {
  const { analyzeUploads, analyzing } = usePatient();
  const [queued, setQueued] = useState<File[]>([]);
  const [stored, setStored] = useState<UploadedFileInfo[]>([]);
  const [clientErrors, setClientErrors] = useState<string[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [processResult, setProcessResult] = useState<ProcessUploadsResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const busy = uploading || analyzing;

  const refreshStored = useCallback(async () => {
    setLoadingList(true);
    try {
      const data = await listUploads();
      setStored(data.files);
    } catch (error) {
      setServerError(getErrorMessage(error));
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    void refreshStored();
  }, [refreshStored]);

  const onFilesSelected = (incoming: File[]) => {
    setServerError(null);
    setSuccessMessage(null);
    setProcessResult(null);
    const { accepted, errors } = validateUploadFiles(incoming, queued);
    setClientErrors(errors);
    if (accepted.length > 0) {
      setQueued((prev) => [...prev, ...accepted]);
    }
  };

  const onUpload = async () => {
    if (queued.length === 0 || busy) return;

    setUploading(true);
    setProgress(0);
    setServerError(null);
    setSuccessMessage(null);
    setProcessResult(null);
    setClientErrors([]);

    try {
      const result = await uploadFiles(queued, (event) => {
        if (!event.total) {
          setProgress(0);
          return;
        }
        setProgress((event.loaded / event.total) * 100);
      });
      setProgress(100);
      setQueued([]);
      setSuccessMessage(`${result.message} Starting AI analysis…`);
      await refreshStored();

      const fileIds = result.files.map((file) => file.file_id);
      const analysis = await analyzeUploads(fileIds);
      setProcessResult(analysis);
      setSuccessMessage(analysis.message);
    } catch (error) {
      setServerError(getErrorMessage(error));
      setProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const onAnalyzeExisting = async () => {
    setServerError(null);
    setProcessResult(null);
    try {
      const analysis = await analyzeUploads();
      setProcessResult(analysis);
      setSuccessMessage(analysis.message);
    } catch (error) {
      setServerError(getErrorMessage(error));
    }
  };

  const onDelete = async (fileId: string) => {
    setDeletingId(fileId);
    setServerError(null);
    try {
      await deleteUpload(fileId);
      setStored((prev) => prev.filter((file) => file.file_id !== fileId));
      setSuccessMessage("File deleted.");
    } catch (error) {
      setServerError(getErrorMessage(error));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section className="space-y-6">
      <PageHeader
        title="Uploads"
        description="Upload medical reports, then the AI extracts medicines, labs, and dates into your patient timeline."
      />
      <p className="text-xs text-surface-500">
        Limits: up to {MAX_UPLOAD_FILES} files · {MAX_UPLOAD_SIZE_MB} MB each · PDF, PNG, JPG, WEBP, TIFF, BMP, GIF
      </p>

      <MedicalDisclaimer text={processResult?.disclaimer} />

      <FileDropzone disabled={busy} onFilesSelected={onFilesSelected} />

      {(clientErrors.length > 0 || serverError) && (
        <div
          role="alert"
          className="whitespace-pre-wrap rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100"
        >
          {clientErrors.length > 0 && (
            <ul className="list-disc space-y-1 pl-5">
              {clientErrors.map((error) => (
                <li key={error}>{error}</li>
              ))}
            </ul>
          )}
          {serverError && <p className={clientErrors.length > 0 ? "mt-2" : undefined}>{serverError}</p>}
        </div>
      )}

      {successMessage && (
        <div
          role="status"
          className="rounded-xl border border-brand-500/30 bg-brand-50 px-4 py-3 text-sm font-medium text-brand-700 dark:border-brand-500/50 dark:bg-brand-900 dark:text-brand-100"
        >
          {successMessage}
        </div>
      )}

      {processResult && (
        <div className="rounded-xl border border-surface-200 bg-white/80 px-4 py-3 text-sm dark:border-surface-700 dark:bg-surface-900/70">
          <p className="font-medium">
            Analysis complete — {processResult.processed} processed
            {processResult.failed ? `, ${processResult.failed} failed` : ""}
            {processResult.skipped ? `, ${processResult.skipped} skipped` : ""}.
          </p>
          <ul className="mt-2 space-y-1 text-surface-600 dark:text-surface-300">
            {processResult.results.map((item) => (
              <li key={item.file_id}>
                {item.filename}: {item.status}
                {item.error ? ` — ${item.error}` : ""}
                {item.status === "completed"
                  ? ` (${item.medicines_count} meds, ${item.labs_count} labs)`
                  : ""}
              </li>
            ))}
          </ul>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to="/dashboard" className="btn-primary">
              Open dashboard
            </Link>
            <Link to="/timeline" className="btn-secondary">
              View timeline
            </Link>
            <Link to="/chat" className="btn-secondary">
              Ask follow-up questions
            </Link>
          </div>
        </div>
      )}

      <QueuedFileList
        files={queued}
        disabled={busy}
        onRemove={(index) => setQueued((prev) => prev.filter((_, i) => i !== index))}
        onClear={() => setQueued([])}
      />

      {uploading && <UploadProgressBar progress={progress} label="Uploading files…" />}
      {analyzing && <UploadProgressBar progress={70} label="AI analyzing reports… this can take a minute" />}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={queued.length === 0 || busy}
          onClick={() => void onUpload()}
          className="btn-primary"
        >
          {uploading
            ? "Uploading…"
            : analyzing
              ? "Analyzing…"
              : `Upload & analyze ${queued.length || ""} file${queued.length === 1 ? "" : "s"}`.trim()}
        </button>
        <button
          type="button"
          disabled={busy || stored.length === 0}
          onClick={() => void onAnalyzeExisting()}
          className="btn-secondary"
        >
          Analyze stored uploads
        </button>
        <button
          type="button"
          disabled={loadingList || busy}
          onClick={() => void refreshStored()}
          className="btn-secondary"
        >
          Refresh list
        </button>
      </div>

      <div className="space-y-3">
        <h2 className="font-display text-xl font-semibold text-surface-900 dark:text-surface-50">
          Stored uploads
        </h2>
        {loadingList ? (
          <p className="text-sm text-surface-500">Loading…</p>
        ) : (
          <StoredUploadsList files={stored} deletingId={deletingId} onDelete={(id) => void onDelete(id)} />
        )}
      </div>
    </section>
  );
}
