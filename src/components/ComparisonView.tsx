import { useMemo, useState } from 'react';
import { Building2, MapPin } from 'lucide-react';
import type { GoldAirQualityDaily } from '@/lib/supabase';
import { getAQIStyle } from '@/lib/supabase';

interface Props {
  goldData: GoldAirQualityDaily[];
  loading: boolean;
}

export default function ComparisonView({ goldData, loading }: Props) {
  const [view, setView] = useState<'city' | 'station'>('city');

  const cityComparison = useMemo(() => {
    const grouped: Record<string, { aqiVals: number[]; pm25Vals: number[]; pm10Vals: number[] }> = {};
    for (const d of goldData) {
      if (!grouped[d.city]) grouped[d.city] = { aqiVals: [], pm25Vals: [], pm10Vals: [] };
      if (d.aqi != null) grouped[d.city].aqiVals.push(d.aqi);
      if (d.avg_pm25 != null) grouped[d.city].pm25Vals.push(d.avg_pm25);
      if (d.avg_pm10 != null) grouped[d.city].pm10Vals.push(d.avg_pm10);
    }
    return Object.entries(grouped).map(([city, vals]) => ({
      city,
      avgAqi: vals.aqiVals.length ? vals.aqiVals.reduce((s, v) => s + v, 0) / vals.aqiVals.length : 0,
      maxAqi: vals.aqiVals.length ? Math.max(...vals.aqiVals) : 0,
      avgPm25: vals.pm25Vals.length ? vals.pm25Vals.reduce((s, v) => s + v, 0) / vals.pm25Vals.length : 0,
      avgPm10: vals.pm10Vals.length ? vals.pm10Vals.reduce((s, v) => s + v, 0) / vals.pm10Vals.length : 0,
      count: vals.aqiVals.length,
    })).sort((a, b) => b.avgAqi - a.avgAqi);
  }, [goldData]);

  const stationComparison = useMemo(() => {
    const grouped: Record<string, { aqiVals: number[]; city: string; name: string }> = {};
    for (const d of goldData) {
      const key = d.station_id;
      if (!grouped[key]) grouped[key] = { aqiVals: [], city: d.city, name: d.station_name };
      if (d.aqi != null) grouped[key].aqiVals.push(d.aqi);
    }
    return Object.entries(grouped).map(([id, vals]) => ({
      stationId: id,
      stationName: vals.name,
      city: vals.city,
      avgAqi: vals.aqiVals.length ? vals.aqiVals.reduce((s, v) => s + v, 0) / vals.aqiVals.length : 0,
      maxAqi: vals.aqiVals.length ? Math.max(...vals.aqiVals) : 0,
      count: vals.aqiVals.length,
    })).sort((a, b) => b.avgAqi - a.avgAqi);
  }, [goldData]);

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-slate-400">Loading comparison data...</div>;
  }

  const maxCityAqi = Math.max(...cityComparison.map((c) => c.avgAqi), 1);
  const maxStationAqi = Math.max(...stationComparison.map((s) => s.avgAqi), 1);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-800">Station / City Comparison</h2>
        <p className="text-sm text-slate-500 mt-1">Compare AQI levels across cities and monitoring stations</p>
      </div>

      {/* Toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setView('city')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${view === 'city' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
        >
          <span className="flex items-center gap-2"><MapPin className="w-4 h-4" /> By City</span>
        </button>
        <button
          onClick={() => setView('station')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${view === 'station' ? 'bg-blue-600 text-white shadow-md' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}`}
        >
          <span className="flex items-center gap-2"><Building2 className="w-4 h-4" /> By Station</span>
        </button>
      </div>

      {/* Chart */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">
          {view === 'city' ? 'Average AQI by City' : 'Average AQI by Station'}
        </h3>
        <div className="space-y-3">
          {view === 'city'
            ? cityComparison.map((c) => {
                const style = getAQIStyle(c.avgAqi <= 50 ? 'Good' : c.avgAqi <= 100 ? 'Satisfactory' : c.avgAqi <= 150 ? 'Moderate' : c.avgAqi <= 200 ? 'Poor' : c.avgAqi <= 300 ? 'Very Poor' : 'Severe');
                return (
                  <div key={c.city} className="flex items-center gap-3">
                    <div className="w-28 text-sm font-medium text-slate-600">{c.city}</div>
                    <div className="flex-1 bg-slate-100 rounded-full h-8 overflow-hidden">
                      <div className="h-full rounded-full flex items-center justify-end pr-3 transition-all duration-500" style={{ width: `${(c.avgAqi / maxCityAqi) * 100}%`, backgroundColor: style.color }}>
                        <span className="text-xs text-white font-bold">{Math.round(c.avgAqi)}</span>
                      </div>
                    </div>
                    <div className="w-16 text-xs text-slate-400 text-right">max {c.maxAqi}</div>
                  </div>
                );
              })
            : stationComparison.map((s) => {
                const style = getAQIStyle(s.avgAqi <= 50 ? 'Good' : s.avgAqi <= 100 ? 'Satisfactory' : s.avgAqi <= 150 ? 'Moderate' : s.avgAqi <= 200 ? 'Poor' : s.avgAqi <= 300 ? 'Very Poor' : 'Severe');
                return (
                  <div key={s.stationId} className="flex items-center gap-3">
                    <div className="w-40 text-sm font-medium text-slate-600 truncate">{s.stationName}</div>
                    <div className="w-20 text-xs text-slate-400">{s.city}</div>
                    <div className="flex-1 bg-slate-100 rounded-full h-8 overflow-hidden">
                      <div className="h-full rounded-full flex items-center justify-end pr-3 transition-all duration-500" style={{ width: `${(s.avgAqi / maxStationAqi) * 100}%`, backgroundColor: style.color }}>
                        <span className="text-xs text-white font-bold">{Math.round(s.avgAqi)}</span>
                      </div>
                    </div>
                    <div className="w-16 text-xs text-slate-400 text-right">max {s.maxAqi}</div>
                  </div>
                );
              })
          }
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">Detailed Comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 text-left">
                {view === 'city' ? (
                  <>
                    <th className="pb-2 pr-4 font-medium">City</th>
                    <th className="pb-2 pr-4 font-medium">Avg AQI</th>
                    <th className="pb-2 pr-4 font-medium">Max AQI</th>
                    <th className="pb-2 pr-4 font-medium">Avg PM2.5</th>
                    <th className="pb-2 pr-4 font-medium">Avg PM10</th>
                    <th className="pb-2 pr-4 font-medium">Records</th>
                  </>
                ) : (
                  <>
                    <th className="pb-2 pr-4 font-medium">Station</th>
                    <th className="pb-2 pr-4 font-medium">City</th>
                    <th className="pb-2 pr-4 font-medium">Avg AQI</th>
                    <th className="pb-2 pr-4 font-medium">Max AQI</th>
                    <th className="pb-2 pr-4 font-medium">Records</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {view === 'city'
                ? cityComparison.map((c) => (
                    <tr key={c.city} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="py-2 pr-4 text-slate-700 font-medium">{c.city}</td>
                      <td className="py-2 pr-4 font-bold text-slate-800">{Math.round(c.avgAqi)}</td>
                      <td className="py-2 pr-4 text-slate-600">{c.maxAqi}</td>
                      <td className="py-2 pr-4 text-slate-600">{c.avgPm25.toFixed(2)}</td>
                      <td className="py-2 pr-4 text-slate-600">{c.avgPm10.toFixed(2)}</td>
                      <td className="py-2 pr-4 text-slate-500">{c.count}</td>
                    </tr>
                  ))
                : stationComparison.map((s) => (
                    <tr key={s.stationId} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="py-2 pr-4 text-slate-700 font-medium">{s.stationName}</td>
                      <td className="py-2 pr-4 text-slate-600">{s.city}</td>
                      <td className="py-2 pr-4 font-bold text-slate-800">{Math.round(s.avgAqi)}</td>
                      <td className="py-2 pr-4 text-slate-600">{s.maxAqi}</td>
                      <td className="py-2 pr-4 text-slate-500">{s.count}</td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
