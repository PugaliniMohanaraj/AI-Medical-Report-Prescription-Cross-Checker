import { formatBytes, formatDate } from "@/utils/upload";
import type { UploadedFileInfo } from "@/types/api";

interface QueuedFileListProps {
  files: File[];
  disabled?: boolean;
  onRemove: (index: number) => void;
  onClear: () => void;
}

export function QueuedFileList({ files, disabled, onRemove, onClear }: QueuedFileListProps) {
  if (files.length === 0) return null;

  return (
    <div className="space-y-3 rounded-xl border border-brand-100 bg-white/80 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-brand-900">
          Ready to upload ({files.length})
        </h2>
        <button
          type="button"
          disabled={disabled}
          onClick={onClear}
          className="text-xs font-medium text-brand-500 hover:text-brand-700 disabled:opacity-50"
        >
          Clear all
        </button>
      </div>
      <ul className="divide-y divide-brand-100">
        {files.map((file, index) => (
          <li key={`${file.name}-${file.size}-${file.lastModified}`} className="flex items-center justify-between gap-3 py-2.5">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-brand-900">{file.name}</p>
              <p className="text-xs text-brand-500">{formatBytes(file.size)}</p>
            </div>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onRemove(index)}
              className="shrink-0 rounded-md px-2 py-1 text-xs text-brand-700 hover:bg-brand-100 disabled:opacity-50"
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface StoredUploadsListProps {
  files: UploadedFileInfo[];
  deletingId?: string | null;
  onDelete: (fileId: string) => void;
}

export function StoredUploadsList({ files, deletingId, onDelete }: StoredUploadsListProps) {
  if (files.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-brand-500/20 bg-white/50 px-4 py-8 text-center text-sm text-brand-500">
        No stored uploads yet.
      </p>
    );
  }

  return (
    <ul className="divide-y divide-brand-100 overflow-hidden rounded-xl border border-brand-100 bg-white/80">
      {files.map((file) => (
        <li key={file.file_id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-brand-900">{file.filename}</p>
            <p className="text-xs text-brand-500">
              {formatBytes(file.size_bytes)} · {formatDate(file.uploaded_at)}
            </p>
            <p className="mt-0.5 truncate font-mono text-[11px] text-brand-500/70">
              {file.file_id}
            </p>
          </div>
          <button
            type="button"
            disabled={deletingId === file.file_id}
            onClick={() => onDelete(file.file_id)}
            className="rounded-md border border-brand-100 px-3 py-1.5 text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50"
          >
            {deletingId === file.file_id ? "Deleting…" : "Delete"}
          </button>
        </li>
      ))}
    </ul>
  );
}
