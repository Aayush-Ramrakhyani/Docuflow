/**
 * Document Review Workspace — the core product differentiator.
 * Split view: document viewer (left) + extraction panel (right).
 */

import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  Edit3,
  FileText,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { documentsApi, type Extraction } from "@/api/documents";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ConfidenceBar } from "@/components/shared/ConfidenceBar";
import {
  formatFileSize,
  formatDateTime,
  formatConfidence,
  getConfidenceLevel,
  formatDocumentType,
  cn,
} from "@/lib/utils";

interface FieldRowProps {
  fieldName: string;
  value: unknown;
  confidence: number | undefined;
  corrected?: unknown;
  onEdit: (field: string, currentValue: string) => void;
}

function FieldRow({ fieldName, value, confidence, corrected, onEdit }: FieldRowProps) {
  // A human correction, when present, always takes precedence over the AI value
  const displayValue = corrected !== undefined ? corrected : value;
  const level = confidence !== undefined ? getConfidenceLevel(confidence) : null;
  const isLowConfidence = level === "low";   // Low-confidence rows are highlighted red for review
  const isCorrected = corrected !== undefined;  // Edited rows are highlighted amber

  return (
    <div
      className={cn(
        "flex items-start gap-3 py-3 border-b border-slate-100 last:border-0 group",
        isLowConfidence && "bg-red-50/50",
        isCorrected && "bg-amber-50/40"
      )}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="text-2xs font-semibold text-slate-500 uppercase tracking-wide">
            {fieldName.replace(/_/g, " ")}
          </span>
          {isCorrected && (
            <span className="text-2xs text-amber-600 font-medium">(edited)</span>
          )}
          {isLowConfidence && !isCorrected && (
            <AlertTriangle className="h-3 w-3 text-red-400" />
          )}
        </div>
        <div className="text-sm text-slate-900 font-mono">
          {displayValue == null ? (
            <span className="text-slate-400 italic">Not found</span>
          ) : typeof displayValue === "object" ? (
            <pre className="text-xs text-slate-700 bg-slate-50 rounded p-2 overflow-auto">
              {JSON.stringify(displayValue, null, 2)}
            </pre>
          ) : (
            String(displayValue)
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {confidence !== undefined && (
          <ConfidenceBar score={confidence} />
        )}
        <button
          onClick={() => onEdit(fieldName, String(displayValue ?? ""))}
          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-slate-200"
          title="Edit field"
        >
          <Edit3 className="h-3 w-3 text-slate-400" />
        </button>
      </div>
    </div>
  );
}

function EditModal({
  field,
  currentValue,
  onSave,
  onClose,
}: {
  field: string;
  currentValue: string;
  onSave: (value: string) => void;
  onClose: () => void;
}) {
  const [value, setValue] = useState(currentValue);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-slate-900/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl border border-slate-200 shadow-modal w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-1">
          Edit field
        </h3>
        <p className="text-xs text-slate-500 mb-4 font-mono uppercase">
          {field.replace(/_/g, " ")}
        </p>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full h-24 px-3 py-2 text-sm border border-slate-200 rounded-md resize-none focus:outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 font-mono"
          autoFocus
        />
        <div className="flex gap-2 mt-4 justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => { onSave(value); onClose(); }}>
            Save correction
          </Button>
        </div>
      </div>
    </div>
  );
}

export function DocumentReviewPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { currentOrgId } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [editingField, setEditingField] = useState<{ field: string; value: string } | null>(null);
  const [approveNotes, setApproveNotes] = useState("");
  const [rejectNotes, setRejectNotes] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const { data: doc, isLoading: docLoading } = useQuery({
    queryKey: ["document", currentOrgId, documentId],
    queryFn: () =>
      documentsApi.get(currentOrgId!, documentId!).then((r) => r.data),
    enabled: !!currentOrgId && !!documentId,
  });

  // Signed URL for the viewer — re-fetched before the 1h signature expires
  const { data: signedUrl } = useQuery({
    queryKey: ["document-url", currentOrgId, documentId],
    queryFn: () =>
      documentsApi
        .getDownloadUrl(currentOrgId!, documentId!)
        .then((r) => r.data),
    enabled: !!currentOrgId && !!documentId && !!doc,
    refetchInterval: 50 * 60 * 1000, // Refresh at 50 min, before the 1h expiry
  });

  // Extraction only exists once processing has produced one — gate the query on status
  const { data: extraction, isLoading: extractionLoading } = useQuery({
    queryKey: ["extraction", currentOrgId, documentId],
    queryFn: () =>
      documentsApi
        .getExtraction(currentOrgId!, documentId!)
        .then((r) => r.data),
    enabled:
      !!currentOrgId &&
      !!documentId &&
      !!doc &&
      ["review_pending", "approved", "rejected", "processed"].includes(doc.status ?? ""),
    retry: false,  // A missing extraction is expected for some statuses — don't retry
  });

  const correctMutation = useMutation({
    mutationFn: ({
      extractionId,
      corrections,
    }: {
      extractionId: string;
      corrections: Record<string, unknown>;
    }) =>
      documentsApi.correctExtraction(currentOrgId!, extractionId, corrections),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["extraction", currentOrgId, documentId] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (extractionId: string) =>
      documentsApi.approveExtraction(currentOrgId!, extractionId, approveNotes || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", currentOrgId, documentId] });
      queryClient.invalidateQueries({ queryKey: ["extraction", currentOrgId, documentId] });
      navigate("/documents");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (extractionId: string) =>
      documentsApi.rejectExtraction(currentOrgId!, extractionId, rejectNotes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", currentOrgId, documentId] });
      navigate("/documents");
    },
  });

  // Save a single-field correction — merged server-side with any prior edits
  const handleEditSave = (field: string, value: string) => {
    if (!extraction) return;
    correctMutation.mutate({
      extractionId: extraction.id,
      corrections: { [field]: value },
    });
  };

  if (docLoading) {
    return (
      <div className="p-8 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64 mb-6" />
        <div className="grid grid-cols-2 gap-6">
          <div className="h-screen bg-slate-100 rounded-xl" />
          <div className="h-screen bg-slate-100 rounded-xl" />
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="p-8">
        <p className="text-sm text-red-500">Document not found.</p>
        <Link to="/documents">
          <Button variant="outline" size="sm" className="mt-4">
            ← Back to Documents
          </Button>
        </Link>
      </div>
    );
  }

  // Derived view state that drives which panels/actions are shown
  const isProcessing = ["queued", "processing"].includes(doc.status);        // Show spinner
  const canReview = doc.status === "review_pending" && extraction;           // Show approve/reject
  const isReviewed = ["approved", "rejected"].includes(doc.status);          // Lock actions

  return (
    <div className="flex flex-col h-screen">
      {/* Review header */}
      <div className="flex items-center justify-between px-6 py-3.5 bg-white border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-3">
          <Link to="/documents">
            <Button variant="ghost" size="icon-sm">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900 text-sm">
                {doc.original_filename}
              </span>
              <StatusBadge status={doc.status} />
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              {formatDocumentType(doc.document_type)} · {formatFileSize(doc.file_size_bytes)}
              {doc.page_count && ` · ${doc.page_count} page${doc.page_count !== 1 ? "s" : ""}`}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        {canReview && !isReviewed && (
          <div className="flex items-center gap-2">
            <Button
              variant="danger-outline"
              size="sm"
              onClick={() => setShowRejectForm(true)}
            >
              <XCircle className="h-3.5 w-3.5" />
              Reject
            </Button>
            <Button
              size="sm"
              onClick={() => approveMutation.mutate(extraction.id)}
              loading={approveMutation.isPending}
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              Approve
            </Button>
          </div>
        )}
      </div>

      {/* Split workspace */}
      <div className="flex flex-1 overflow-hidden">
        {/* Document viewer */}
        <div className="flex-1 bg-slate-100 overflow-auto flex flex-col">
          {signedUrl ? (
            <div className="flex-1 relative">
              {doc.mime_type === "application/pdf" ? (
                <iframe
                  src={signedUrl.url}
                  className="w-full h-full border-0"
                  title="Document preview"
                />
              ) : (
                <div className="p-6 flex justify-center">
                  <img
                    src={signedUrl.url}
                    alt="Document preview"
                    className="max-w-full rounded-lg shadow-elevated"
                  />
                </div>
              )}
              <a
                href={signedUrl.url}
                target="_blank"
                rel="noopener noreferrer"
                className="absolute top-4 right-4 flex items-center gap-1.5 bg-white/90 backdrop-blur-sm rounded-md px-2.5 py-1.5 text-xs text-slate-600 border border-slate-200 shadow-sm hover:bg-white transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                Open full
              </a>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FileText className="h-12 w-12 text-slate-300 mx-auto mb-3" />
                <p className="text-sm text-slate-500">
                  {isProcessing ? "Document is being processed…" : "Preview unavailable"}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Extraction panel */}
        <div className="w-96 bg-white border-l border-slate-200 overflow-y-auto shrink-0 flex flex-col">
          <div className="p-5 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-900 mb-1">
              Extracted Data
            </h2>
            {extraction && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  Overall confidence:
                </span>
                <ConfidenceBar
                  score={extraction.overall_confidence ?? 0}
                  showLabel
                />
              </div>
            )}
          </div>

          {isProcessing && (
            <div className="p-6 text-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-amber-500 border-t-transparent mx-auto mb-3" />
              <p className="text-sm text-slate-600">Processing document…</p>
              <p className="text-xs text-slate-400 mt-1">This may take a moment</p>
            </div>
          )}

          {doc.status === "failed" && (
            <div className="p-5">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm font-medium text-red-700">Processing failed</p>
                {doc.status_message && (
                  <p className="text-xs text-red-500 mt-1">{doc.status_message}</p>
                )}
              </div>
            </div>
          )}

          {extraction && !isProcessing && (
            <div className="flex-1">
              {/* Extraction metadata */}
              <div className="px-5 py-3 bg-slate-50 border-b border-slate-100">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-slate-400">Model:</span>{" "}
                    <span className="font-mono text-slate-600">{extraction.model_used}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Tokens:</span>{" "}
                    <span className="font-mono text-slate-600">
                      {extraction.tokens_used?.toLocaleString() ?? "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Status:</span>{" "}
                    <StatusBadge status={extraction.status} />
                  </div>
                  <div>
                    <span className="text-slate-400">Time:</span>{" "}
                    <span className="font-mono text-slate-600">
                      {extraction.processing_time_ms
                        ? `${(extraction.processing_time_ms / 1000).toFixed(1)}s`
                        : "—"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Extracted fields */}
              <div className="px-5">
                {Object.entries(extraction.final_data).length > 0 ? (
                  Object.entries(extraction.final_data).map(([field, value]) => (
                    <FieldRow
                      key={field}
                      fieldName={field}
                      value={value}
                      confidence={extraction.confidence_scores[field]}
                      corrected={extraction.corrected_data?.[field]}
                      onEdit={(f, v) => setEditingField({ field: f, value: v })}
                    />
                  ))
                ) : (
                  <div className="py-8 text-center text-sm text-slate-400">
                    No fields extracted
                  </div>
                )}
              </div>

              {/* Review notes */}
              {extraction.review_notes && (
                <div className="mx-5 my-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs font-medium text-amber-700 mb-1">Review notes</p>
                  <p className="text-xs text-amber-600">{extraction.review_notes}</p>
                </div>
              )}
            </div>
          )}

          {/* Reject form */}
          {showRejectForm && (
            <div className="p-5 border-t border-slate-200 bg-red-50/50">
              <p className="text-sm font-medium text-slate-700 mb-2">
                Reason for rejection
              </p>
              <textarea
                value={rejectNotes}
                onChange={(e) => setRejectNotes(e.target.value)}
                placeholder="Describe why this extraction is being rejected…"
                className="w-full h-24 px-3 py-2 text-sm border border-slate-200 rounded-md resize-none focus:outline-none focus:border-red-400"
              />
              <div className="flex gap-2 mt-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowRejectForm(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  disabled={!rejectNotes.trim()}
                  loading={rejectMutation.isPending}
                  onClick={() => rejectMutation.mutate(extraction!.id)}
                >
                  Confirm rejection
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Edit modal */}
      {editingField && (
        <EditModal
          field={editingField.field}
          currentValue={editingField.value}
          onSave={(v) => handleEditSave(editingField.field, v)}
          onClose={() => setEditingField(null)}
        />
      )}
    </div>
  );
}
