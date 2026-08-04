import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from "react";

import { cn } from "@/utils/cn";

interface FileDropzoneProps {
  disabled?: boolean;
  onFilesSelected: (files: File[]) => void;
}

export function FileDropzone({ disabled = false, onFilesSelected }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const emitFiles = useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return;
      onFilesSelected(Array.from(list));
    },
    [onFilesSelected],
  );

  const onDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    if (!disabled) setIsDragging(true);
  };

  const onDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
    if (disabled) return;
    emitFiles(event.dataTransfer.files);
  };

  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    emitFiles(event.target.files);
    event.target.value = "";
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-disabled={disabled}
      onKeyDown={(event) => {
        if (disabled) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => {
        if (!disabled) inputRef.current?.click();
      }}
      className={cn(
        "cursor-pointer rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-colors",
        isDragging
          ? "border-brand-500 bg-brand-100/70 dark:bg-brand-900/40"
          : "border-brand-500/30 bg-white/70 hover:border-brand-500/60 hover:bg-white dark:bg-surface-900/60 dark:hover:bg-surface-900",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf,image/png,image/jpeg,image/webp,image/tiff,image/bmp,image/gif,.png,.jpg,.jpeg,.webp,.tif,.tiff,.bmp,.gif"
        multiple
        className="hidden"
        disabled={disabled}
        onChange={onChange}
      />
      <p className="font-display text-xl font-semibold text-surface-900 dark:text-surface-50">
        {isDragging ? "Drop files here" : "Drag & drop reports"}
      </p>
      <p className="mt-2 text-sm text-surface-600 dark:text-surface-300">
        PDF or images (PNG, JPG, WEBP, TIFF, BMP, GIF) — multiple files supported
      </p>
    </div>
  );
}
