import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useDropzone } from "react-dropzone";
import { Link } from "react-router-dom";
import {
  Upload,
  FileText,
  Search,
  Filter,
  Trash2,
  Eye,
  RefreshCw,
} from "lucide-react";
import { documentsApi } from "@/api/documents";
import { useAuthStore } from "@/stores/auth-store";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/shared/StatusBadge";
import {
  formatFileSize,
  formatRelativeTime,
  formatDocumentType,
} from "@/lib/utils";

function UploadZone({ orgId }: { orgId: string }) {
  const queryClient = useQueryClient();
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsApi.upload(orgId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", orgId] });
      queryClient.invalidateQueries({ queryKey: ["analytics", "overview", orgId] });
    },
    onError: (err: any) => {
      setUploadError(err.response?.data?.detail ?? "Upload failed");
    },
  });

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploadError(null);
      setUploading(true);
      for (const file of acceptedFiles) {
        await uploadMutation.mutateAsync(file).catch(() => {});
      }
      setUploading(false);
    },
    [uploadMutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/tiff": [".tif", ".tiff"],
      "image/webp": [".webp"],
    },
    maxSize: 50 * 1024 * 1024,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors duration-150 ${
        isDragActive
          ? "border-amber-400 bg-amber-50"
          : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <input {...getInputProps()} />
      <div className="flex justify-center mb-3">
        <div
          className={`flex h-12 w-12 items-center justify-center rounded-xl transition-colors ${
            isDragActive ? "bg-amber-100" : "bg-slate-100"
          }`}
        >
          <Upload
            className={`h-5 w-5 ${isDragActive ? "text-amber-600" : "text-slate-400"}`}
          />
        </div>
      </div>
      <p className="text-sm font-medium text-slate-700">
        {uploading
          ? "Uploading…"
          : isDragActive
          ? "Drop to upload"
          : "Drop files here or click to browse"}
      </p>
      <p className="text-xs text-slate-400 mt-1">
        PDF, JPEG, PNG, TIFF, WebP — max 50 MB
      </p>
      {uploadError && (
        <p className="mt-2 text-xs text-red-500">{uploadError}</p>
      )}
    </div>
  );
}

export function DocumentsPage() {
  const { currentOrgId } = useAuthStore();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const ACTIVE_STATUSES = new Set(["uploaded", "queued", "processing"]);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["documents", currentOrgId, page, search, statusFilter],
    queryFn: () =>
      documentsApi
        .list(currentOrgId!, {
          page,
          page_size: 20,
          search: search || undefined,
          status: statusFilter || undefined,
        })
        .then((r) => r.data),
    enabled: !!currentOrgId,
    // Only poll while at least one document is actively being processed
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      return items.some((d) => ACTIVE_STATUSES.has(d.status)) ? 4000 : false;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (docId: string) => documentsApi.delete(currentOrgId!, docId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["documents", currentOrgId] }),
  });

  if (!currentOrgId) {
    return (
      <div className="p-8">
        <p className="text-sm text-slate-500">Select an organization to continue.</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Documents</h1>
          <p className="page-subtitle">
            Upload and manage your documents for processing
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={() => refetch()}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Upload zone */}
      <div className="mb-6">
        <UploadZone orgId={currentOrgId} />
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search documents…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full h-9 pl-9 pr-3 text-sm border border-slate-200 rounded-md bg-white focus:outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="h-9 px-3 text-sm border border-slate-200 rounded-md bg-white text-slate-700 focus:outline-none focus:border-amber-500"
        >
          <option value="">All statuses</option>
          <option value="uploaded">Uploaded</option>
          <option value="processing">Processing</option>
          <option value="review_pending">Pending Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Documents table */}
      <Card>
        {isLoading ? (
          <div className="p-8 space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />
            ))}
          </div>
        ) : data && data.items.length > 0 ? (
          <>
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    File
                  </th>
                  <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Type
                  </th>
                  <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Status
                  </th>
                  <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Pages
                  </th>
                  <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Size
                  </th>
                  <th className="px-5 py-3 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Uploaded
                  </th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody>
                {data.items.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                        <span className="text-sm text-slate-900 font-medium truncate max-w-[220px]">
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-500">
                      {formatDocumentType(doc.document_type)}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-5 py-3 text-sm font-mono text-slate-500">
                      {doc.page_count ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-sm font-mono text-slate-500">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-400">
                      {formatRelativeTime(doc.created_at)}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-1 justify-end">
                        <Link to={`/documents/${doc.id}/review`}>
                          <Button size="icon-sm" variant="ghost">
                            <Eye className="h-3.5 w-3.5" />
                          </Button>
                        </Link>
                        <Button
                          size="icon-sm"
                          variant="ghost"
                          onClick={() => {
                            if (confirm(`Delete "${doc.original_filename}"?`)) {
                              deleteMutation.mutate(doc.id);
                            }
                          }}
                          className="text-slate-400 hover:text-red-500 hover:bg-red-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100">
              <span className="text-xs text-slate-500">
                {data.total} document{data.total !== 1 ? "s" : ""}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <span className="flex items-center px-3 text-sm text-slate-600">
                  Page {page}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!data.has_next}
                >
                  Next
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="px-5 py-16 text-center">
            <FileText className="h-12 w-12 text-slate-200 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-500">No documents found</p>
            <p className="text-xs text-slate-400 mt-1">
              {search || statusFilter
                ? "Try adjusting your filters"
                : "Upload a document above to get started"}
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
