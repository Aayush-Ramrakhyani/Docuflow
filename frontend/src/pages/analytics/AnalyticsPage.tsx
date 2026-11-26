/**
 * Analytics page.
 *
 * Deeper view of the same analytics overview the dashboard uses: KPI row plus
 * two recharts bar charts (documents by status, top document types). All data
 * comes from one overview query, reshaped client-side for the charts.
 */

import { useQuery } from "@tanstack/react-query";
import { BarChart3, TrendingUp, FileText, CheckCircle2 } from "lucide-react";
import { analyticsApi } from "@/api/analytics";
import { useAuthStore } from "@/stores/auth-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDocumentType } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

const STATUS_COLORS: Record<string, string> = {
  approved: "#22C55E",
  review_pending: "#F59E0B",
  processing: "#3B82F6",
  failed: "#EF4444",
  uploaded: "#94A3B8",
  queued: "#60A5FA",
  rejected: "#F87171",
};

export function AnalyticsPage() {
  const { currentOrgId } = useAuthStore();

  const { data: overview, isLoading } = useQuery({
    queryKey: ["analytics", "overview", currentOrgId],
    queryFn: () =>
      analyticsApi.getOverview(currentOrgId!).then((r) => r.data),
    enabled: !!currentOrgId,
  });

  // Status map → bar data, each bar colored by its status
  const statusChartData = overview
    ? Object.entries(overview.status_breakdown).map(([name, value]) => ({
        name: name.replace(/_/g, " "),
        value,
        fill: STATUS_COLORS[name] ?? "#94A3B8",
      }))
    : [];

  // Document types, sorted by frequency, top 8 only
  const typeChartData = overview
    ? Object.entries(overview.document_type_breakdown)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 8)
        .map(([name, value]) => ({ name: formatDocumentType(name), value }))
    : [];

  if (isLoading) {
    return (
      <div className="p-8 animate-pulse space-y-6">
        <div className="h-8 bg-slate-200 rounded w-40" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-slate-200 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="page-header">
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Processing insights and document intelligence metrics</p>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          {
            label: "Total Documents",
            value: overview?.total_documents ?? 0,
            icon: FileText,
          },
          {
            label: "Total Extractions",
            value: overview?.total_extractions ?? 0,
            icon: TrendingUp,
          },
          {
            label: "Avg. Confidence",
            value: `${Math.round((overview?.average_confidence ?? 0) * 100)}%`,
            icon: BarChart3,
          },
          {
            label: "Pending Review",
            value: overview?.pending_review ?? 0,
            icon: CheckCircle2,
          },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="pt-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
                    {label}
                  </div>
                  <div className="text-2xl font-bold text-slate-900">{value}</div>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100">
                  <Icon className="h-4 w-4 text-slate-500" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Documents by Status</CardTitle>
          </CardHeader>
          <CardContent>
            {statusChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={statusChartData} barSize={28}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "#64748B" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#64748B" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      border: "1px solid #E2E8F0",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {statusChartData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-sm text-slate-400">
                No data yet
              </div>
            )}
          </CardContent>
        </Card>

        {/* Document types */}
        <Card>
          <CardHeader>
            <CardTitle>Document Types</CardTitle>
          </CardHeader>
          <CardContent>
            {typeChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={typeChartData}
                  layout="vertical"
                  barSize={18}
                  margin={{ left: 16 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11, fill: "#64748B" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "#64748B" }}
                    axisLine={false}
                    tickLine={false}
                    width={100}
                  />
                  <Tooltip
                    contentStyle={{
                      border: "1px solid #E2E8F0",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                  <Bar dataKey="value" fill="#F59E0B" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-sm text-slate-400">
                No document types detected yet
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
