import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  Clock,
  CheckCircle2,
  TrendingUp,
  ArrowRight,
} from "lucide-react";
import { Link } from "react-router-dom";
import { analyticsApi } from "@/api/analytics";
import { documentsApi } from "@/api/documents";
import { useAuthStore } from "@/stores/auth-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatFileSize, formatRelativeTime, formatDocumentType } from "@/lib/utils";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

function KPICard({
  title,
  value,
  icon: Icon,
  description,
  accent,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description?: string;
  accent?: boolean;
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
              {title}
            </div>
            <div className={`text-2xl font-bold ${accent ? "text-amber-600" : "text-slate-900"}`}>
              {value}
            </div>
            {description && (
              <div className="text-xs text-slate-400 mt-1">{description}</div>
            )}
          </div>
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-lg ${
              accent ? "bg-amber-100" : "bg-slate-100"
            }`}
          >
            <Icon className={`h-4.5 w-4.5 ${accent ? "text-amber-600" : "text-slate-500"}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

const STATUS_COLORS: Record<string, string> = {
  approved: "#22C55E",
  review_pending: "#F59E0B",
  processing: "#3B82F6",
  failed: "#EF4444",
  uploaded: "#94A3B8",
  queued: "#60A5FA",
};

export function DashboardPage() {
  const { currentOrgId } = useAuthStore();

  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ["analytics", "overview", currentOrgId],
    queryFn: () =>
      analyticsApi.getOverview(currentOrgId!).then((r) => r.data),
    enabled: !!currentOrgId,
  });

  const { data: recentDocs } = useQuery({
    queryKey: ["documents", currentOrgId, "recent"],
    queryFn: () =>
      documentsApi
        .list(currentOrgId!, { page: 1, page_size: 5 })
        .then((r) => r.data),
    enabled: !!currentOrgId,
  });

  const pieData = overview
    ? Object.entries(overview.status_breakdown).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  if (overviewLoading) {
    return (
      <div className="p-8 animate-pulse space-y-4">
        <div className="h-8 bg-slate-200 rounded w-48" />
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
      {/* Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Overview of your document processing workspace</p>
        </div>
        <Link to="/documents">
          <Button size="sm">
            <FileText className="h-3.5 w-3.5" />
            Upload document
          </Button>
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard
          title="Total Documents"
          value={overview?.total_documents ?? 0}
          icon={FileText}
        />
        <KPICard
          title="Pending Review"
          value={overview?.pending_review ?? 0}
          icon={Clock}
          accent
        />
        <KPICard
          title="Total Extractions"
          value={overview?.total_extractions ?? 0}
          icon={TrendingUp}
        />
        <KPICard
          title="Avg. Confidence"
          value={`${Math.round((overview?.average_confidence ?? 0) * 100)}%`}
          icon={CheckCircle2}
          description="AI extraction accuracy"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Document type breakdown */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={75}
                    innerRadius={45}
                  >
                    {pieData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={STATUS_COLORS[entry.name] ?? "#94A3B8"}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      border: "1px solid #E2E8F0",
                      borderRadius: "8px",
                      fontSize: "12px",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-48 flex items-center justify-center text-sm text-slate-400">
                No data yet
              </div>
            )}

            {/* Legend */}
            <div className="mt-3 space-y-1.5">
              {pieData.slice(0, 5).map(({ name, value }) => (
                <div key={name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{ background: STATUS_COLORS[name] ?? "#94A3B8" }}
                    />
                    <span className="text-xs text-slate-600 capitalize">
                      {name.replace(/_/g, " ")}
                    </span>
                  </div>
                  <span className="text-xs font-mono text-slate-500">{value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Document types */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Document Types</CardTitle>
          </CardHeader>
          <CardContent>
            {overview && Object.keys(overview.document_type_breakdown).length > 0 ? (
              <div className="space-y-3 mt-1">
                {Object.entries(overview.document_type_breakdown)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 6)
                  .map(([type, count]) => {
                    const max = Math.max(
                      ...Object.values(overview.document_type_breakdown)
                    );
                    const pct = max > 0 ? (count / max) * 100 : 0;
                    return (
                      <div key={type} className="flex items-center gap-3">
                        <div className="text-sm text-slate-600 w-32 truncate">
                          {formatDocumentType(type)}
                        </div>
                        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-amber-400 rounded-full transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <div className="text-xs font-mono text-slate-500 w-8 text-right">
                          {count}
                        </div>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <div className="h-48 flex items-center justify-center text-sm text-slate-400">
                Upload documents to see type distribution
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent documents */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Documents</CardTitle>
          <Link
            to="/documents"
            className="text-sm text-amber-600 hover:text-amber-700 flex items-center gap-1"
          >
            View all <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </CardHeader>
        <div>
          {recentDocs && recentDocs.items.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-5 py-2.5 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Document
                  </th>
                  <th className="px-5 py-2.5 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Type
                  </th>
                  <th className="px-5 py-2.5 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Status
                  </th>
                  <th className="px-5 py-2.5 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Size
                  </th>
                  <th className="px-5 py-2.5 text-left text-2xs font-semibold text-slate-500 uppercase tracking-wide">
                    Uploaded
                  </th>
                </tr>
              </thead>
              <tbody>
                {recentDocs.items.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2.5">
                        <FileText className="h-4 w-4 text-slate-400 shrink-0" />
                        <Link
                          to={`/documents/${doc.id}/review`}
                          className="text-sm text-slate-900 hover:text-amber-600 font-medium truncate max-w-[200px]"
                        >
                          {doc.original_filename}
                        </Link>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-500">
                      {formatDocumentType(doc.document_type)}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-5 py-3 text-sm font-mono text-slate-500">
                      {formatFileSize(doc.file_size_bytes)}
                    </td>
                    <td className="px-5 py-3 text-sm text-slate-400">
                      {formatRelativeTime(doc.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="px-5 py-12 text-center">
              <FileText className="h-10 w-10 text-slate-200 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-500">No documents yet</p>
              <p className="text-xs text-slate-400 mt-1">Upload your first document to get started</p>
              <Link to="/documents">
                <Button size="sm" className="mt-4">
                  Upload document
                </Button>
              </Link>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
