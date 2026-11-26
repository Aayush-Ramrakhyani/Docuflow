/**
 * Documents & extractions API client.
 *
 * Thin typed wrappers over the axios instance. The interfaces mirror the
 * backend Pydantic response models so components get end-to-end typing.
 */

import { apiClient } from "./client";

export interface Document {
  id: string;
  organization_id: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  page_count: number | null;
  document_type: string | null;
  status: string;
  status_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface Extraction {
  id: string;
  document_id: string;
  extracted_data: Record<string, unknown>;
  confidence_scores: Record<string, number>;
  overall_confidence: number | null;
  corrected_data: Record<string, unknown> | null;
  final_data: Record<string, unknown>;
  status: string;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  review_notes: string | null;
  model_used: string;
  tokens_used: number | null;
  processing_time_ms: number | null;
  created_at: string;
  updated_at: string;
}

export const documentsApi = {
  upload: (orgId: string, file: File) => {
    // multipart/form-data upload — the raw file, validated server-side by magic bytes
    const formData = new FormData();
    formData.append("file", file);
    return apiClient.post<{ document: Document; job_id: string }>(
      `/organizations/${orgId}/documents`,
      formData,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
  },

  list: (
    orgId: string,
    params?: {
      status?: string;
      document_type?: string;
      search?: string;
      page?: number;
      page_size?: number;
    }
  ) =>
    apiClient.get<DocumentListResponse>(`/organizations/${orgId}/documents`, {
      params,
    }),

  get: (orgId: string, docId: string) =>
    apiClient.get<Document>(`/organizations/${orgId}/documents/${docId}`),

  getDownloadUrl: (orgId: string, docId: string) =>
    apiClient.get<{ url: string; expires_in: number }>(
      `/organizations/${orgId}/documents/${docId}/download`
    ),

  delete: (orgId: string, docId: string) =>
    apiClient.delete(`/organizations/${orgId}/documents/${docId}`),

  getExtraction: (orgId: string, docId: string) =>
    apiClient.get<Extraction>(
      `/organizations/${orgId}/extractions/by-document/${docId}`
    ),

  correctExtraction: (
    orgId: string,
    extractionId: string,
    corrections: Record<string, unknown>,
    notes?: string
  ) =>
    apiClient.patch<Extraction>(
      `/organizations/${orgId}/extractions/${extractionId}/correct`,
      { corrections, notes }
    ),

  approveExtraction: (orgId: string, extractionId: string, notes?: string) =>
    apiClient.post<Extraction>(
      `/organizations/${orgId}/extractions/${extractionId}/approve`,
      { notes }
    ),

  rejectExtraction: (orgId: string, extractionId: string, notes: string) =>
    apiClient.post<Extraction>(
      `/organizations/${orgId}/extractions/${extractionId}/reject`,
      { notes }
    ),
};
