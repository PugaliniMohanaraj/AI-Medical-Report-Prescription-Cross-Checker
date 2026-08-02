export const MAX_UPLOAD_FILES = 10;
export const MAX_UPLOAD_SIZE_MB = 20;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(value: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export interface LocalFileValidation {
  accepted: File[];
  errors: string[];
}

export function validatePdfFiles(
  incoming: File[],
  alreadyQueued: File[] = [],
): LocalFileValidation {
  const errors: string[] = [];
  const accepted: File[] = [];
  const existingKeys = new Set(
    alreadyQueued.map((file) => `${file.name}:${file.size}:${file.lastModified}`),
  );

  for (const file of incoming) {
    const key = `${file.name}:${file.size}:${file.lastModified}`;
    if (existingKeys.has(key)) {
      errors.push(`"${file.name}" is already in the queue.`);
      continue;
    }

    const isPdfMime = file.type === "application/pdf" || file.type === "";
    const isPdfName = file.name.toLowerCase().endsWith(".pdf");
    if (!isPdfName || (!isPdfMime && file.type !== "application/octet-stream")) {
      errors.push(`"${file.name}" is not a PDF.`);
      continue;
    }

    if (file.size === 0) {
      errors.push(`"${file.name}" is empty.`);
      continue;
    }

    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      errors.push(`"${file.name}" exceeds the ${MAX_UPLOAD_SIZE_MB} MB limit.`);
      continue;
    }

    accepted.push(file);
    existingKeys.add(key);
  }

  if (alreadyQueued.length + accepted.length > MAX_UPLOAD_FILES) {
    const allowed = Math.max(0, MAX_UPLOAD_FILES - alreadyQueued.length);
    return {
      accepted: accepted.slice(0, allowed),
      errors: [
        ...errors,
        `You can upload at most ${MAX_UPLOAD_FILES} files at once.`,
      ],
    };
  }

  return { accepted, errors };
}
