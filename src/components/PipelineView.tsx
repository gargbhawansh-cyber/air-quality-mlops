import { useMemo } from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Database, ShieldCheck } from 'lucide-react';
import type { PipelineRun, DataQualitySummary, IngestionRun, RejectedRecord } from '@/lib/supabase';

interface Props {
  pipelineRuns: PipelineRun[];
  qualitySummaries: DataQualitySummary[];
  ingestionRuns: IngestionRun[];
  rejectedRecords: RejectedRecord[];
  loading: boolean;
}

export default function PipelineView({ pipelineRuns, qualitySummaries, ingestionRuns, rejectedRecords, loading }: Props) {
  const latestRun = pipelineRuns[0];
  const latestQuality = useMemo(() => {
    return qualitySummaries.filter((q) => q.pipeline_run_id === latestRun?.run_id);
  }, [qualitySummaries, latestRun]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Loading pipeline data...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Data Pipeline Status</h2>
        <p className="text-sm text-slate-500 mt-1">Pipeline execution metadata, data quality summaries, and ingestion logs</p>
      </div>

      {/* Pipeline run status */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800">Latest Pipeline Run</h3>
          {latestRun && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
              style={{
                backgroundColor: latestRun.status === 'success' ? '#dcfce7' : latestRun.status === 'failed' ? '#fee2e2' : '#fef9c3',
                color: latestRun.status === 'success' ? '#16a34a' : latestRun.status === 'failed' ? '#dc2626' : '#ca8a04',
              }}>
              {latestRun.status === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
              {latestRun.status.toUpperCase()}
            </div>
          )}
        </div>
        {latestRun ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            <Field label="Run ID" value={latestRun.run_id} mono />
            <Field label="Started" value={new Date(latestRun.started_at).toLocaleString()} />
            <Field label="Completed" value={latestRun.completed_at ? new Date(latestRun.completed_at).toLocaleString() : '—'} />
            <Field label="Status" value={latestRun.status} />
            <Field label="Total Records" value={latestRun.total_records.toLocaleString()} />
            <Field label="Valid Records" value={latestRun.valid_records.toLocaleString()} />
            <Field label="Rejected" value={latestRun.rejected_records.toLocaleString()} />
            <Field label="Duplicates" value={latestRun.duplicate_records.toLocaleString()} />
            <Field label="Missing Values" value={latestRun.missing_value_count.toLocaleString()} />
            <Field label="Validation Failures" value={latestRun.validation_failures.toLocaleString()} />
            <Field label="Gold Records" value={latestRun.gold_records.toLocaleString()} />
            {latestRun.error_message && <Field label="Error" value={latestRun.error_message} />}
          </div>
        ) : (
          <div className="text-slate-400 text-sm">No pipeline runs recorded</div>
        )}
      </div>

      {/* Data quality summaries */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-slate-800">Data Quality Summary</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left">
                <th className="pb-2 pr-4 font-medium">Source</th>
                <th className="pb-2 pr-4 font-medium">Total</th>
                <th className="pb-2 pr-4 font-medium">Valid</th>
                <th className="pb-2 pr-4 font-medium">Rejected</th>
                <th className="pb-2 pr-4 font-medium">Duplicates</th>
                <th className="pb-2 pr-4 font-medium">Missing</th>
                <th className="pb-2 pr-4 font-medium">Failures</th>
                <th className="pb-2 pr-4 font-medium">Schema</th>
                <th className="pb-2 pr-4 font-medium">Checks Passed</th>
                <th className="pb-2 pr-4 font-medium">Checks Failed</th>
              </tr>
            </thead>
            <tbody>
              {latestQuality.map((q) => (
                <tr key={q.summary_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-2 pr-4 text-slate-700 font-medium">{q.source}</td>
                  <td className="py-2 pr-4 text-slate-600">{q.total_records.toLocaleString()}</td>
                  <td className="py-2 pr-4 text-green-600 font-medium">{q.valid_records.toLocaleString()}</td>
                  <td className="py-2 pr-4 text-red-600">{q.rejected_records}</td>
                  <td className="py-2 pr-4 text-slate-600">{q.duplicate_records}</td>
                  <td className="py-2 pr-4 text-slate-600">{q.missing_value_count}</td>
                  <td className="py-2 pr-4 text-slate-600">{q.validation_failures}</td>
                  <td className="py-2 pr-4">
                    {q.schema_valid ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : <XCircle className="w-4 h-4 text-red-500" />}
                  </td>
                  <td className="py-2 pr-4 text-green-600">{q.checks_passed}</td>
                  <td className="py-2 pr-4 text-red-600">{q.checks_failed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ingestion runs */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-slate-800">Ingestion Run History</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left">
                <th className="pb-2 pr-4 font-medium">Run ID</th>
                <th className="pb-2 pr-4 font-medium">Source</th>
                <th className="pb-2 pr-4 font-medium">Extraction Time</th>
                <th className="pb-2 pr-4 font-medium">Status</th>
                <th className="pb-2 pr-4 font-medium">Row Count</th>
                <th className="pb-2 pr-4 font-medium">Data Source</th>
                <th className="pb-2 pr-4 font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {ingestionRuns.slice(0, 10).map((r) => (
                <tr key={r.run_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-2 pr-4 font-mono text-xs text-slate-500">{r.run_id}</td>
                  <td className="py-2 pr-4 text-slate-700 font-medium">{r.source}</td>
                  <td className="py-2 pr-4 text-slate-600">{new Date(r.extraction_time).toLocaleString()}</td>
                  <td className="py-2 pr-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-slate-600">{r.row_count.toLocaleString()}</td>
                  <td className="py-2 pr-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${r.data_source === 'live' ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'}`}>
                      {r.data_source.toUpperCase()}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-slate-400 text-xs max-w-xs truncate">{r.error_message ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rejected records */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h3 className="text-lg font-semibold text-slate-800">Rejected Records ({rejectedRecords.length})</h3>
        </div>
        {rejectedRecords.length === 0 ? (
          <div className="text-slate-400 text-sm">No rejected records in the latest run</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 text-left">
                  <th className="pb-2 pr-4 font-medium">ID</th>
                  <th className="pb-2 pr-4 font-medium">Reason</th>
                  <th className="pb-2 pr-4 font-medium">Rule</th>
                  <th className="pb-2 pr-4 font-medium">Rejected At</th>
                </tr>
              </thead>
              <tbody>
                {rejectedRecords.slice(0, 20).map((r) => (
                  <tr key={r.rejected_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="py-2 pr-4 text-slate-500">{r.rejected_id}</td>
                    <td className="py-2 pr-4 text-red-600 font-medium">{r.rejection_reason}</td>
                    <td className="py-2 pr-4 text-slate-600 font-mono text-xs">{r.validation_rule ?? '—'}</td>
                    <td className="py-2 pr-4 text-slate-500">{new Date(r.rejected_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
      <div className={`text-sm text-slate-700 mt-0.5 ${mono ? 'font-mono text-xs' : 'font-medium'}`}>{value}</div>
    </div>
  );
}
