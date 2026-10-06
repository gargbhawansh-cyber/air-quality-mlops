import { useMemo, useState } from 'react';
import { BarChart3 } from 'lucide-react';
import type { AirQualityMeasurement } from '@/lib/supabase';

interface Props {
  aqData: AirQualityMeasurement[];
  loading: boolean;
}

const POLLUTANTS = ['pm25', 'pm10', 'co', 'no2', 'so2', 'o3'];
const POLLUTANT_LABELS: Record<string, string> = {
  pm25: 'PM2.5', pm10: 'PM10', co: 'CO', no2: 'NO2', so2: 'SO2', o3: 'O3',
};

export default function PollutantView({ aqData, loading }: Props) {
  const [selectedPollutant, setSelectedPollutant] = useState<string>('pm25');

  const pollutantData = useMemo(() => {
    return aqData.filter((d) => d.pollutant === selectedPollutant);
  }, [aqData, selectedPollutant]);

  const stats = useMemo(() => {
    if (!pollutantData.length) return null;
    const values = pollutantData.map((d) => d.value).filter((v) => v != null);
    if (!values.length) return null;
    return {
      min: Math.min(...values),
      max: Math.max(...values),
      avg: values.reduce((s, v) => s + v, 0) / values.length,
      count: values.length,
    };
  }, [pollutantData]);

  // City-wise breakdown
  const cityStats = useMemo(() => {
    const grouped: Record<string, number[]> = {};
    for (const r of pollutantData) {
      if (!grouped[r.city]) grouped[r.city] = [];
      grouped[r.city].push(r.value);
    }
    return Object.entries(grouped).map(([city, vals]) => ({
      city,
      avg: vals.reduce((s, v) => s + v, 0) / vals.length,
      min: Math.min(...vals),
      max: Math.max(...vals),
      count: vals.length,
    })).sort((a, b) => b.avg - a.avg);
  }, [pollutantData]);

  // Time series for the pollutant
  const timeSeries = useMemo(() => {
    const grouped: Record<string, number[]> = {};
    for (const r of pollutantData) {
      const hour = r.measurement_time.slice(0, 13);
      if (!grouped[hour]) grouped[hour] = [];
      grouped[hour].push(r.value);
    }
    return Object.entries(grouped)
      .map(([hour, vals]) => ({ hour, avg: vals.reduce((s, v) => s + v, 0) / vals.length }))
      .sort((a, b) => a.hour.localeCompare(b.hour));
  }, [pollutantData]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Loading pollutant data...</div>;
  }

  const maxCityAvg = Math.max(...cityStats.map((c) => c.avg), 1);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Pollutant Analysis</h2>
        <p className="text-sm text-slate-500 mt-1">Distribution and trends for individual pollutants</p>
      </div>

      {/* Pollutant selector */}
      <div className="flex flex-wrap gap-2">
        {POLLUTANTS.map((p) => (
          <button
            key={p}
            onClick={() => setSelectedPollutant(p)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              selectedPollutant === p
                ? 'bg-blue-600 text-white shadow-md'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
            }`}
          >
            {POLLUTANT_LABELS[p]}
          </button>
        ))}
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Average" value={stats.avg.toFixed(2)} unit={pollutantData[0]?.unit ?? ''} />
          <StatCard label="Minimum" value={stats.min.toFixed(2)} unit={pollutantData[0]?.unit ?? ''} />
          <StatCard label="Maximum" value={stats.max.toFixed(2)} unit={pollutantData[0]?.unit ?? ''} />
          <StatCard label="Measurements" value={stats.count.toString()} unit="" />
        </div>
      )}

      {/* City comparison bar chart */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-slate-800">{POLLUTANT_LABELS[selectedPollutant]} — Average by City</h3>
        </div>
        <div className="space-y-3">
          {cityStats.map((c) => (
            <div key={c.city} className="flex items-center gap-3">
              <div className="w-24 text-sm font-medium text-slate-600">{c.city}</div>
              <div className="flex-1 bg-slate-100 rounded-full h-7 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-blue-400 to-blue-600 flex items-center justify-end pr-2 transition-all duration-500"
                  style={{ width: `${(c.avg / maxCityAvg) * 100}%` }}
                >
                  <span className="text-xs text-white font-medium">{c.avg.toFixed(1)}</span>
                </div>
              </div>
              <div className="w-20 text-xs text-slate-400 text-right">{c.count} obs</div>
            </div>
          ))}
        </div>
      </div>

      {/* Time series */}
      {timeSeries.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">{POLLUTANT_LABELS[selectedPollutant]} — Hourly Average Trend</h3>
          <TimeSeriesChart data={timeSeries} />
        </div>
      )}

      {/* Detailed table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">City-wise Statistics</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left">
                <th className="pb-2 pr-4 font-medium">City</th>
                <th className="pb-2 pr-4 font-medium">Average</th>
                <th className="pb-2 pr-4 font-medium">Minimum</th>
                <th className="pb-2 pr-4 font-medium">Maximum</th>
                <th className="pb-2 pr-4 font-medium">Observations</th>
              </tr>
            </thead>
            <tbody>
              {cityStats.map((c) => (
                <tr key={c.city} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-2 pr-4 text-slate-700 font-medium">{c.city}</td>
                  <td className="py-2 pr-4 text-slate-600">{c.avg.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-slate-600">{c.min.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-slate-600">{c.max.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-slate-500">{c.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
      <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-2xl font-bold text-slate-800 mt-1">{value}</div>
      {unit && <div className="text-xs text-slate-400 mt-0.5">{unit}</div>}
    </div>
  );
}

function TimeSeriesChart({ data }: { data: { hour: string; avg: number }[] }) {
  const width = Math.max(data.length * 20, 600);
  const height = 240;
  const padding = { top: 15, right: 15, bottom: 35, left: 45 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;
  const maxVal = Math.max(...data.map((d) => d.avg), 1);

  const xScale = (i: number) => padding.left + (data.length > 1 ? (i / (data.length - 1)) * innerW : 0);
  const yScale = (v: number) => padding.top + innerH - (v / maxVal) * innerH;

  const linePath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.avg)}`).join(' ');

  return (
    <div className="overflow-x-auto">
      <svg width={width} height={height} className="min-w-full">
        {[0, 0.5, 1].map((p) => {
          const y = padding.top + innerH - p * innerH;
          return (
            <g key={p}>
              <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#e2e8f0" />
              <text x={padding.left - 8} y={y + 4} textAnchor="end" className="text-xs fill-slate-400">{Math.round(p * maxVal)}</text>
            </g>
          );
        })}
        <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth={2} />
        {data.map((d, i) => (
          <circle key={i} cx={xScale(i)} cy={yScale(d.avg)} r={3} fill="#3b82f6" />
        ))}
        {data.filter((_, i) => i % Math.ceil(data.length / 8) === 0).map((d, i) => {
          const idx = data.indexOf(d);
          return (
            <text key={i} x={xScale(idx)} y={height - 8} textAnchor="middle" className="text-xs fill-slate-400">
              {d.hour.slice(11, 16)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
