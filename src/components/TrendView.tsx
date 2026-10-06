import { useMemo, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import type { GoldAirQualityDaily } from '@/lib/supabase';
import { getAQIStyle } from '@/lib/supabase';

interface Props {
  goldData: GoldAirQualityDaily[];
  loading: boolean;
}

export default function TrendView({ goldData, loading }: Props) {
  const [cityFilter, setCityFilter] = useState<string>('all');
  const [stationFilter, setStationFilter] = useState<string>('all');

  const cities = useMemo(() => Array.from(new Set(goldData.map((d) => d.city))).sort(), [goldData]);
  const stations = useMemo(() => {
    const filtered = cityFilter === 'all' ? goldData : goldData.filter((d) => d.city === cityFilter);
    return Array.from(new Set(filtered.map((d) => `${d.station_id}|${d.station_name}`))).sort();
  }, [goldData, cityFilter]);

  const filtered = useMemo(() => {
    return goldData
      .filter((d) => cityFilter === 'all' || d.city === cityFilter)
      .filter((d) => stationFilter === 'all' || d.station_id === stationFilter.split('|')[0])
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [goldData, cityFilter, stationFilter]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Loading trend data...</div>;
  }

  const chartData = filtered.map((d) => ({
    date: d.date,
    aqi: d.aqi,
    category: d.aqi_category,
    city: d.city,
    station: d.station_name,
  }));

  const maxAqi = Math.max(...chartData.map((d) => d.aqi ?? 0), 1);
  const chartWidth = Math.max(chartData.length * 60, 600);
  const chartHeight = 320;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  const innerWidth = chartWidth - padding.left - padding.right;
  const innerHeight = chartHeight - padding.top - padding.bottom;

  const xScale = (i: number) => padding.left + (chartData.length > 1 ? (i / (chartData.length - 1)) * innerWidth : 0);
  const yScale = (val: number) => padding.top + innerHeight - (val / maxAqi) * innerHeight;

  const linePath = chartData.map((d, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.aqi ?? 0)}`).join(' ');
  const areaPath = `${linePath} L ${xScale(chartData.length - 1)} ${padding.top + innerHeight} L ${xScale(0)} ${padding.top + innerHeight} Z`;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">AQI Trend Analysis</h2>
        <p className="text-sm text-slate-500 mt-1">Air Quality Index over time with interactive filters</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">City</label>
          <select
            value={cityFilter}
            onChange={(e) => { setCityFilter(e.target.value); setStationFilter('all'); }}
            className="px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Cities</option>
            {cities.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Station</label>
          <select
            value={stationFilter}
            onChange={(e) => setStationFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Stations</option>
            {stations.map((s) => {
              const [id, name] = s.split('|');
              return <option key={id} value={s}>{name}</option>;
            })}
          </select>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-blue-500" />
          <h3 className="text-lg font-semibold text-slate-800">AQI Over Time</h3>
        </div>
        {chartData.length === 0 ? (
          <div className="text-center text-slate-400 py-12">No data for selected filters</div>
        ) : (
          <div className="overflow-x-auto">
            <svg width={chartWidth} height={chartHeight} className="min-w-full">
              {/* Grid lines */}
              {[0, 0.25, 0.5, 0.75, 1].map((p) => {
                const y = padding.top + innerHeight - p * innerHeight;
                const val = Math.round(p * maxAqi);
                return (
                  <g key={p}>
                    <line x1={padding.left} y1={y} x2={chartWidth - padding.right} y2={y} stroke="#e2e8f0" strokeWidth={1} />
                    <text x={padding.left - 8} y={y + 4} textAnchor="end" className="text-xs fill-slate-400">{val}</text>
                  </g>
                );
              })}
              {/* Area */}
              <defs>
                <linearGradient id="aqiGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <path d={areaPath} fill="url(#aqiGradient)" />
              {/* Line */}
              <path d={linePath} fill="none" stroke="#3b82f6" strokeWidth={2} />
              {/* Points */}
              {chartData.map((d, i) => {
                const style = getAQIStyle(d.category);
                return (
                  <g key={i}>
                    <circle cx={xScale(i)} cy={yScale(d.aqi ?? 0)} r={5} fill={style.color} stroke="white" strokeWidth={2} />
                    <text x={xScale(i)} y={padding.top + innerHeight + 20} textAnchor="middle" className="text-xs fill-slate-500">
                      {d.date.slice(5)}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        )}
      </div>

      {/* Data Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Trend Data</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left">
                <th className="pb-2 pr-4 font-medium">Date</th>
                <th className="pb-2 pr-4 font-medium">City</th>
                <th className="pb-2 pr-4 font-medium">Station</th>
                <th className="pb-2 pr-4 font-medium">AQI</th>
                <th className="pb-2 pr-4 font-medium">Category</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice().reverse().map((row) => {
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
