import { apiClient } from "./client";

export interface AnalyticsOverview {
  total_documents: number;
  pending_review: number;
  total_extractions: number;
  average_confidence: number;
  status_breakdown: Record<string, number>;
  job_breakdown: Record<string, number>;
  document_type_breakdown: Record<string, number>;
}

export const analyticsApi = {
  getOverview: (orgId: string) =>
    apiClient.get<AnalyticsOverview>(`/organizations/${orgId}/analytics/overview`),
};
