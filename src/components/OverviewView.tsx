import { useMemo } from 'react';
import { Activity, Database, AlertTriangle, CheckCircle2, Clock, Building2, Gauge } from 'lucide-react';
import type { GoldAirQualityDaily, PipelineRun, IngestionRun } from '@/lib/supabase';
import { getAQIStyle } from '@/lib/supabase';

interface Props {
  goldData: GoldAirQualityDaily[];
  pipelineRuns: PipelineRun[];
  ingestionRuns: IngestionRun[];
  loading: boolean;
}

export default function OverviewView({ goldData, pipelineRuns, ingestionRuns, loading }: Props) {
  const stats = useMemo(() => {
    if (!goldData.length) return null;
    const latest = [...goldData].sort((a, b) => b.date.localeCompare(a.date))[0];
    const aqiValues = goldData.map((d) => d.aqi).filter((v): v is number => v != null);
    const avgAqi = aqiValues.length ? Math.round(aqiValues.reduce((s, v) => s + v, 0) / aqiValues.length) : 0;
    const maxAqi = aqiValues.length ? Math.max(...aqiValues) : 0;
    const stations = new Set(goldData.map((d) => d.station_id));
    const totalObs = goldData.reduce((s, d) => s + (d.observation_count || 0), 0);
    return { latest, avgAqi, maxAqi, stationCount: stations.size, totalObs };
  }, [goldData]);

  const latestPipeline = pipelineRuns[0];
  const latestIngestion = ingestionRuns[0];
  const dataSrc = latestIngestion?.data_source ?? 'unknown';

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Loading overview data...</div>;
  }

  if (!stats) {
    return <div className="flex items-center justify-center h-64 text-slate-400">No data available. Run the pipeline first.</div>;
  }

  const aqiStyle = getAQIStyle(stats.latest?.aqi_category);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">AQI Overview</h2>
        <p className="text-sm text-slate-500 mt-1">Current air quality index and key metrics from the analytical data mart</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <KPICard
          label="Latest AQI"
          value={stats.latest?.aqi?.toString() ?? '—'}
          sub={stats.latest?.aqi_category ?? '—'}
          icon={<Gauge className="w-5 h-5" />}
          accentColor={aqiStyle.color}
          accentBg={aqiStyle.bg}
        />
        <KPICard
          label="Average AQI"
          value={stats.avgAqi.toString()}
          sub="across all records"
          icon={<Activity className="w-5 h-5" />}
          accentColor="#3b82f6"
          accentBg="#dbeafe"
        />
        <KPICard
          label="Highest AQI"
          value={stats.maxAqi.toString()}
          sub="peak reading"
          icon={<AlertTriangle className="w-5 h-5" />}
          accentColor="#ef4444"
          accentBg="#fee2e2"
        />
        <KPICard
          label="Total Stations"
          value={stats.stationCount.toString()}
          sub="monitoring sites"
          icon={<Building2 className="w-5 h-5" />}
          accentColor="#8b5cf6"
          accentBg="#ede9fe"
        />
        <KPICard
          label="Total Observations"
          value={stats.totalObs.toLocaleString()}
          sub="measurements"
          icon={<Database className="w-5 h-5" />}
          accentColor="#06b6d4"
          accentBg="#cffafe"
        />
        <KPICard
          label="Cities Monitored"
          value={new Set(goldData.map((d) => d.city)).size.toString()}
          sub="locations"
          icon={<Clock className="w-5 h-5" />}
          accentColor="#10b981"
          accentBg="#d1fae5"
        />
      </div>

      {/* Pipeline Status */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-slate-800">Data Pipeline Status</h3>
          <PipelineBadge status={latestPipeline?.status ?? 'unknown'} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <StatItem label="Pipeline Run" value={latestPipeline?.run_id ?? '—'} mono />
          <StatItem label="Status" value={latestPipeline?.status ?? '—'} />
          <StatItem label="Total Records" value={latestPipeline?.total_records.toLocaleString() ?? '—'} />
          <StatItem label="Valid Records" value={latestPipeline?.valid_records.toLocaleString() ?? '—'} />
          <StatItem label="Rejected" value={latestPipeline?.rejected_records.toLocaleString() ?? '—'} />
          <StatItem label="Gold Records" value={latestPipeline?.gold_records.toLocaleString() ?? '—'} />
          <StatItem label="Duplicates" value={latestPipeline?.duplicate_records.toLocaleString() ?? '—'} />
          <StatItem label="Missing Values" value={latestPipeline?.missing_value_count.toLocaleString() ?? '—'} />
          <StatItem label="Validation Failures" value={latestPipeline?.validation_failures.toLocaleString() ?? '—'} />
          <StatItem label="Data Source" value={dataSrc.toUpperCase()} />
          <StatItem label="Started" value={latestPipeline?.started_at ? new Date(latestPipeline.started_at).toLocaleString() : '—'} />
          <StatItem label="Completed" value={latestPipeline?.completed_at ? new Date(latestPipeline.completed_at).toLocaleString() : '—'} />
        </div>
      </div>

      {/* Latest AQI by Station */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Latest AQI by Station</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left">
                <th className="pb-2 pr-4 font-medium">Date</th>
                <th className="pb-2 pr-4 font-medium">City</th>
                <th className="pb-2 pr-4 font-medium">Station</th>
                <th className="pb-2 pr-4 font-medium">AQI</th>
                <th className="pb-2 pr-4 font-medium">Category</th>
                <th className="pb-2 pr-4 font-medium">PM2.5</th>
                <th className="pb-2 pr-4 font-medium">PM10</th>
                <th className="pb-2 pr-4 font-medium">Observations</th>
              </tr>
            </thead>
            <tbody>
              {goldData
                .filter((d) => d.date === stats.latest?.date)
                .map((row) => {
                  const style = getAQIStyle(row.aqi_category);
                  return (
                    <tr key={`${row.station_id}-${row.date}`} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="py-2 pr-4 text-slate-600">{row.date}</td>
                      <td className="py-2 pr-4 text-slate-700 font-medium">{row.city}</td>
                      <td className="py-2 pr-4 text-slate-600">{row.station_name}</td>
                      <td className="py-2 pr-4 font-bold" style={{ color: style.color }}>{row.aqi ?? '—'}</td>
                      <td className="py-2 pr-4">
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium" style={{ color: style.color, backgroundColor: style.bg }}>
                          {row.aqi_category ?? '—'}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-slate-600">{row.avg_pm25?.toFixed(2) ?? '—'}</td>
                      <td className="py-2 pr-4 text-slate-600">{row.avg_pm10?.toFixed(2) ?? '—'}</td>
                      <td className="py-2 pr-4 text-slate-500">{row.observation_count}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KPICard({ label, value, sub, icon, accentColor, accentBg }: {
  label: string; value: string; sub: string; icon: React.ReactNode; accentColor: string; accentBg: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</span>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: accentBg, color: accentColor }}>
          {icon}
        </div>
      </div>
      <div className="text-2xl font-bold text-slate-800">{value}</div>
      <div className="text-xs text-slate-400 mt-1">{sub}</div>
    </div>
  );
}

function StatItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-xs text-slate-400 uppercase tracking-wide">{label}</div>
      <div className={`text-sm text-slate-700 mt-0.5 ${mono ? 'font-mono text-xs' : 'font-medium'}`}>{value}</div>
    </div>
  );
}

function PipelineBadge({ status }: { status: string }) {
  const isSuccess = status === 'success';
  const isFailed = status === 'failed';
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
      style={{
        backgroundColor: isSuccess ? '#dcfce7' : isFailed ? '#fee2e2' : '#fef9c3',
        color: isSuccess ? '#16a34a' : isFailed ? '#dc2626' : '#ca8a04',
      }}>
      {isSuccess ? <CheckCircle2 className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
      {status.toUpperCase()}
    </div>
  );
}
