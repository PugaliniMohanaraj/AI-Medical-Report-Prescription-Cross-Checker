import { useCallback, useEffect, useState } from "react";

import { getErrorMessage } from "@/api/client";
import { deleteUpload, listUploads, uploadPdfs } from "@/api/endpoints";
import { FileDropzone } from "@/components/FileDropzone";
import { QueuedFileList, StoredUploadsList } from "@/components/UploadFileLists";
import { UploadProgressBar } from "@/components/UploadProgressBar";
import type { UploadedFileInfo } from "@/types/api";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  MAX_UPLOAD_FILES,
  MAX_UPLOAD_SIZE_MB,
  validatePdfFiles,
} from "@/utils/upload";

export function UploadPage() {
  const [queued, setQueued] = useState<File[]>([]);
  const [stored, setStored] = useState<UploadedFileInfo[]>([]);
  const [clientErrors, setClientErrors] = useState<string[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

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
    const { accepted, errors } = validatePdfFiles(incoming, queued);
    setClientErrors(errors);
    if (accepted.length > 0) {
      setQueued((prev) => [...prev, ...accepted]);
    }
  };

  const onUpload = async () => {
    if (queued.length === 0 || uploading) return;

    setUploading(true);
    setProgress(0);
    setServerError(null);
    setSuccessMessage(null);
    setClientErrors([]);

    try {
      const result = await uploadPdfs(queued, (event) => {
        if (!event.total) {
          setProgress(0);
          return;
        }
        setProgress((event.loaded / event.total) * 100);
      });
      setProgress(100);
      setQueued([]);
      setSuccessMessage(result.message);
      await refreshStored();
    } catch (error) {
      setServerError(getErrorMessage(error));
      setProgress(0);
    } finally {
      setUploading(false);
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
        description="Upload multiple PDF medical reports and prescriptions. Files are validated, stored, and tracked in metadata."
      />
      <p className="text-xs text-surface-500">
        Limits: up to {MAX_UPLOAD_FILES} PDFs · {MAX_UPLOAD_SIZE_MB} MB each
      </p>

      <FileDropzone disabled={uploading} onFilesSelected={onFilesSelected} />

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
          className="rounded-xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-700 dark:border-brand-800 dark:bg-brand-950/40 dark:text-brand-100"
        >
          {successMessage}
        </div>
      )}

      <QueuedFileList
        files={queued}
        disabled={uploading}
        onRemove={(index) => setQueued((prev) => prev.filter((_, i) => i !== index))}
        onClear={() => setQueued([])}
      />

      {uploading && <UploadProgressBar progress={progress} label="Uploading PDFs…" />}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={queued.length === 0 || uploading}
          onClick={() => void onUpload()}
          className="btn-primary"
        >
          {uploading ? "Uploading…" : `Upload ${queued.length || ""} PDF${queued.length === 1 ? "" : "s"}`.trim()}
        </button>
        <button
          type="button"
          disabled={loadingList || uploading}
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
