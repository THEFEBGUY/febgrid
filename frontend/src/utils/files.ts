import type { Attachment } from "../types/api";

const supportedImageExtensions = new Set([".png", ".jpg", ".jpeg", ".webp"]);
const supportedImageContentTypes = new Set(["image/png", "image/jpeg", "image/webp"]);
const supportedAudioExtensions = new Set([".mp3", ".wav", ".m4a", ".webm", ".ogg"]);
const supportedAudioContentTypes = new Set([
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/x-wav",
  "audio/mp4",
  "audio/x-m4a",
  "audio/webm",
  "audio/ogg",
  "application/ogg",
]);

function extensionFromName(fileName: string): string {
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex >= 0 ? fileName.slice(dotIndex).toLowerCase() : "";
}

export function isSupportedImageAttachment(attachment: Attachment): boolean {
  const extension = (attachment.extension || extensionFromName(attachment.original_file_name)).toLowerCase();
  const contentType = (attachment.content_type || "").toLowerCase();
  return supportedImageExtensions.has(extension) || supportedImageContentTypes.has(contentType);
}

export function isSupportedAudioAttachment(attachment: Attachment): boolean {
  const extension = (attachment.extension || extensionFromName(attachment.original_file_name)).toLowerCase();
  const contentType = (attachment.content_type || "").toLowerCase();
  return supportedAudioExtensions.has(extension) || supportedAudioContentTypes.has(contentType);
}
