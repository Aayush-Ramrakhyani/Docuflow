/**
 * StatusBadge — maps a raw status string (document or job) to a human label and
 * a colored Badge variant. Centralizing the mapping keeps status styling
 * consistent everywhere it appears (tables, headers, review panel).
 */

import { Badge } from "@/components/ui/badge";
import { getStatusColor } from "@/lib/utils";

// Raw status → display label
const STATUS_LABELS: Record<string, string> = {
  uploaded: "Uploaded",
  queued: "Queued",
  processing: "Processing",
  processed: "Processed",
  review_pending: "Pending Review",
  approved: "Approved",
  rejected: "Rejected",
  failed: "Failed",
  pending_review: "Pending Review",
  completed: "Completed",
  running: "Running",
};

// Raw status → Badge color variant
const STATUS_VARIANTS: Record<string, "default" | "success" | "warning" | "error" | "info" | "amber"> = {
  uploaded: "default",
  queued: "info",
  processing: "amber",
  processed: "success",
  review_pending: "amber",
  pending_review: "amber",
  approved: "success",
  rejected: "error",
  failed: "error",
  completed: "success",
  running: "info",
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const label = STATUS_LABELS[status] ?? status;
  const variant = STATUS_VARIANTS[status] ?? "default";
  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
}
