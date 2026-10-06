import { useMemo } from 'react';
import { Cloud, Droplets, Thermometer, Wind } from 'lucide-react';
import type { GoldAirQualityDaily } from '@/lib/supabase';

interface Props {
  goldData: GoldAirQualityDaily[];
  loading: boolean;
}

export default function WeatherView({ goldData, loading }: Props) {
  const correlations = useMemo(() => {
    const valid = goldData.filter((d) => d.aqi != null);
    if (valid.length < 2) return null;

    function corr(a: (number | null)[], b: (number | null)[]) {
      const pairs: [number, number][] = [];
      for (let i = 0; i < a.length; i++) {
        if (a[i] != null && b[i] != null) pairs.push([a[i]!, b[i]!]);
      }
      if (pairs.length < 2) return 0;
      const n = pairs.length;
      const meanA = pairs.reduce((s, [x]) => s + x, 0) / n;
      const meanB = pairs.reduce((s, [, y]) => s + y, 0) / n;
      let num = 0, denA = 0, denB = 0;
      for (const [x, y] of pairs) {
        num += (x - meanA) * (y - meanB);
        denA += (x - meanA) ** 2;
        denB += (y - meanB) ** 2;
      }
      const den = Math.sqrt(denA * denB);
      return den === 0 ? 0 : num / den;
    }

    const aqi = valid.map((d) => d.aqi);
    return {
      temperature: corr(aqi, valid.map((d) => d.avg_temperature)),
      humidity: corr(aqi, valid.map((d) => d.avg_humidity)),
      rainfall: corr(aqi, valid.map((d) => d.avg_rainfall)),
      windSpeed: corr(aqi, valid.map((d) => d.avg_wind_speed)),
    };
  }, [goldData]);

  const scatterData = useMemo(() => {
    return goldData.filter((d) => d.aqi != null && d.avg_temperature != null);
  }, [goldData]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Loading weather data...</div>;
  }

  if (!correlations) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Insufficient data for weather correlation analysis</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Weather Impact Analysis</h2>
        <p className="text-sm text-slate-500 mt-1">Correlation between weather conditions and air quality</p>
      </div>

      {/* Correlation cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <CorrCard label="Temperature vs AQI" value={correlations.temperature} icon={<Thermometer className="w-5 h-5" />} color="#ef4444" bg="#fee2e2" />
        <CorrCard label="Humidity vs AQI" value={correlations.humidity} icon={<Droplets className="w-5 h-5" />} color="#3b82f6" bg="#dbeafe" />
        <CorrCard label="Rainfall vs AQI" value={correlations.rainfall} icon={<Cloud className="w-5 h-5" />} color="#06b6d4" bg="#cffafe" />
        <CorrCard label="Wind Speed vs AQI" value={correlations.windSpeed} icon={<Wind className="w-5 h-5" />} color="#10b981" bg="#d1fae5" />
      </div>

      {/* Scatter plot: AQI vs Temperature */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">AQI vs Temperature</h3>
        <ScatterPlot data={scatterData.map((d) => ({ x: d.avg_temperature!, y: d.aqi!, label: d.city }))} xLabel="Temperature (°C)" yLabel="AQI" />
      </div>

      {/* Weather summary table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Weather & AQI Summary by City</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left">
                <th className="pb-2 pr-4 font-medium">City</th>
                <th className="pb-2 pr-4 font-medium">Avg AQI</th>
                <th className="pb-2 pr-4 font-medium">Avg Temp</th>
                <th className="pb-2 pr-4 font-medium">Avg Humidity</th>
                <th className="pb-2 pr-4 font-medium">Avg Rainfall</th>
                <th className="pb-2 pr-4 font-medium">Avg Wind</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(
                goldData.reduce((acc, d) => {
                  if (!acc[d.city]) acc[d.city] = { aqi: [], temp: [], hum: [], rain: [], wind: [] };
                  if (d.aqi != null) acc[d.city].aqi.push(d.aqi);
                  if (d.avg_temperature != null) acc[d.city].temp.push(d.avg_temperature);
                  if (d.avg_humidity != null) acc[d.city].hum.push(d.avg_humidity);
                  if (d.avg_rainfall != null) acc[d.city].rain.push(d.avg_rainfall);
                  if (d.avg_wind_speed != null) acc[d.city].wind.push(d.avg_wind_speed);
                  return acc;
                }, {} as Record<string, { aqi: number[]; temp: number[]; hum: number[]; rain: number[]; wind: number[] }>)
              ).map(([city, vals]) => (
                <tr key={city} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="py-2 pr-4 text-slate-700 font-medium">{city}</td>
                  <td className="py-2 pr-4 font-bold text-slate-800">{vals.aqi.length ? Math.round(vals.aqi.reduce((s, v) => s + v, 0) / vals.aqi.length) : '—'}</td>
                  <td className="py-2 pr-4 text-slate-600">{vals.temp.length ? (vals.temp.reduce((s, v) => s + v, 0) / vals.temp.length).toFixed(1) : '—'}</td>
                  <td className="py-2 pr-4 text-slate-600">{vals.hum.length ? (vals.hum.reduce((s, v) => s + v, 0) / vals.hum.length).toFixed(1) : '—'}</td>
                  <td className="py-2 pr-4 text-slate-600">{vals.rain.length ? (vals.rain.reduce((s, v) => s + v, 0) / vals.rain.length).toFixed(2) : '—'}</td>
                  <td className="py-2 pr-4 text-slate-600">{vals.wind.length ? (vals.wind.reduce((s, v) => s + v, 0) / vals.wind.length).toFixed(1) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function CorrCard({ label, value, icon, color, bg }: { label: string; value: number; icon: React.ReactNode; color: string; bg: string }) {
  const strength = Math.abs(value);
  const direction = value > 0 ? 'positive' : value < 0 ? 'negative' : 'none';
  const strengthLabel = strength > 0.7 ? 'Strong' : strength > 0.4 ? 'Moderate' : strength > 0.2 ? 'Weak' : 'Negligible';
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</span>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: bg, color }}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-slate-800">{value.toFixed(3)}</div>
      <div className="text-xs text-slate-400 mt-1">{strengthLabel} {direction} correlation</div>
    </div>
  );
}

function ScatterPlot({ data, xLabel, yLabel }: { data: { x: number; y: number; label: string }[]; xLabel: string; yLabel: string }) {
  const width = 700;
  const height = 350;
  const padding = { top: 20, right: 20, bottom: 45, left: 55 };
  const innerW = width - padding.left - padding.right;
  const innerH = height - padding.top - padding.bottom;

  const xMin = Math.min(...data.map((d) => d.x));
  const xMax = Math.max(...data.map((d) => d.x));
  const yMin = Math.min(...data.map((d) => d.y));
  const yMax = Math.max(...data.map((d) => d.y));
  const xRange = xMax - xMin || 1;
  const yRange = yMax - yMin || 1;

  const xScale = (v: number) => padding.left + ((v - xMin) / xRange) * innerW;
  const yScale = (v: number) => padding.top + innerH - ((v - yMin) / yRange) * innerH;

  const colors = ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'];
  const cityColor: Record<string, string> = {};
  let ci = 0;
  for (const d of data) {
    if (!cityColor[d.label]) { cityColor[d.label] = colors[ci % colors.length]; ci++; }
  }

  return (
    <svg width={width} height={height} className="w-full">
      {[0, 0.25, 0.5, 0.75, 1].map((p) => {
        const y = padding.top + innerH - p * innerH;
        const val = Math.round(yMin + p * yRange);
        return (
          <g key={p}>
            <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#e2e8f0" />
            <text x={padding.left - 8} y={y + 4} textAnchor="end" className="text-xs fill-slate-400">{val}</text>
          </g>
        );
      })}
      {[0, 0.25, 0.5, 0.75, 1].map((p) => {
        const x = padding.left + p * innerW;
        const val = (xMin + p * xRange).toFixed(1);
        return (
          <g key={p}>
            <line x1={x} y1={padding.top} x2={x} y2={padding.top + innerH} stroke="#e2e8f0" />
            <text x={x} y={height - 20} textAnchor="middle" className="text-xs fill-slate-400">{val}</text>
          </g>
        );
      })}
      {data.map((d, i) => (
        <circle key={i} cx={xScale(d.x)} cy={yScale(d.y)} r={5} fill={cityColor[d.label]} fillOpacity={0.7} stroke="white" strokeWidth={1} />
      ))}
      <text x={width / 2} y={height - 5} textAnchor="middle" className="text-xs fill-slate-500">{xLabel}</text>
      <text x={15} y={height / 2} textAnchor="middle" transform={`rotate(-90 15 ${height / 2})`} className="text-xs fill-slate-500">{yLabel}</text>
    </svg>
  );
}
