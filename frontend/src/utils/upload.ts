export const MAX_UPLOAD_FILES = 10;
export const MAX_UPLOAD_SIZE_MB = 20;
export const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

const ALLOWED_EXTENSIONS = new Set([
  ".pdf",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".tif",
  ".tiff",
  ".bmp",
  ".gif",
]);

const ALLOWED_MIME_TYPES = new Set([
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
  "image/tiff",
  "image/bmp",
  "image/x-ms-bmp",
  "image/gif",
  "application/octet-stream",
  "",
]);

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

function fileExtension(name: string): string {
  const index = name.lastIndexOf(".");
  return index >= 0 ? name.slice(index).toLowerCase() : "";
}

export function validateUploadFiles(
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

    const extension = fileExtension(file.name);
    const mime = file.type.toLowerCase();
    const extensionOk = ALLOWED_EXTENSIONS.has(extension);
    const mimeOk = ALLOWED_MIME_TYPES.has(mime);

    if (!extensionOk || !mimeOk) {
      errors.push(
        `"${file.name}" is not a supported file. Use PDF or images (PNG, JPG, WEBP, TIFF, BMP, GIF).`,
      );
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

/** @deprecated Use validateUploadFiles */
export const validatePdfFiles = validateUploadFiles;
