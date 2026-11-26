/**
 * Shared frontend utilities: className merging, date/size/confidence formatting,
 * and status-color mapping. Pure functions, no side effects — safe to use anywhere.
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

// Merge conditional classes and dedupe conflicting Tailwind utilities
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(dateString: string): string {
  return formatDistanceToNow(new Date(dateString), { addSuffix: true });
}

export function formatDate(dateString: string): string {
  return format(new Date(dateString), "MMM d, yyyy");
}

export function formatDateTime(dateString: string): string {
  return format(new Date(dateString), "MMM d, yyyy 'at' HH:mm");
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatConfidence(score: number): string {
  return `${Math.round(score * 100)}%`;
}

// Bucket a 0–1 confidence score — drives the color coding in the review UI
export function getConfidenceLevel(score: number): "high" | "medium" | "low" {
  if (score >= 0.9) return "high";    // Green — trust as-is
  if (score >= 0.7) return "medium";  // Neutral
  return "low";                       // Red — flag for human review
}

export function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    uploaded: "bg-slate-100 text-slate-600 border-slate-200",
    queued: "bg-blue-50 text-blue-700 border-blue-200",
    processing: "bg-amber-50 text-amber-700 border-amber-200",
    processed: "bg-green-50 text-green-700 border-green-200",
    review_pending: "bg-amber-50 text-amber-700 border-amber-200",
    approved: "bg-green-50 text-green-700 border-green-200",
    rejected: "bg-red-50 text-red-700 border-red-200",
    failed: "bg-red-50 text-red-700 border-red-200",
    pending_review: "bg-amber-50 text-amber-700 border-amber-200",
  };
  return map[status] ?? "bg-slate-100 text-slate-600 border-slate-200";
}

export function formatDocumentType(type: string | null | undefined): string {
  if (!type) return "Unknown";
  return type
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 1) + "…";
}
