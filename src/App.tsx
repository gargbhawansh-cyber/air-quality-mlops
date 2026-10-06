import { useEffect, useState } from 'react';
import { Activity, BarChart3, Building2, Cloud, Gauge, GitBranch, Database, Wind } from 'lucide-react';
import OverviewView from '@/components/OverviewView';
import TrendView from '@/components/TrendView';
import PollutantView from '@/components/PollutantView';
import ComparisonView from '@/components/ComparisonView';
import WeatherView from '@/components/WeatherView';
import PipelineView from '@/components/PipelineView';
import {
  fetchGoldData, fetchAQMeasurements, fetchWeatherMeasurements,
  fetchIngestionRuns, fetchPipelineRuns, fetchQualitySummaries, fetchRejectedRecords,
  type GoldAirQualityDaily, type AirQualityMeasurement,
  type PipelineRun, type DataQualitySummary, type IngestionRun, type RejectedRecord,
} from '@/lib/supabase';

type ViewKey = 'overview' | 'trend' | 'pollutant' | 'comparison' | 'weather' | 'pipeline';

const NAV_ITEMS: { key: ViewKey; label: string; icon: React.ReactNode; desc: string }[] = [
  { key: 'overview', label: 'AQI Overview', icon: <Gauge className="w-5 h-5" />, desc: 'Key metrics & KPIs' },
  { key: 'trend', label: 'AQI Trend', icon: <Activity className="w-5 h-5" />, desc: 'Time-series analysis' },
  { key: 'pollutant', label: 'Pollutant Analysis', icon: <BarChart3 className="w-5 h-5" />, desc: 'By pollutant type' },
  { key: 'comparison', label: 'City / Station', icon: <Building2 className="w-5 h-5" />, desc: 'Comparative analysis' },
  { key: 'weather', label: 'Weather Impact', icon: <Cloud className="w-5 h-5" />, desc: 'Correlation analysis' },
  { key: 'pipeline', label: 'Pipeline Status', icon: <Database className="w-5 h-5" />, desc: 'Data quality & runs' },
];

export default function App() {
  const [activeView, setActiveView] = useState<ViewKey>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [goldData, setGoldData] = useState<GoldAirQualityDaily[]>([]);
  const [aqData, setAqData] = useState<AirQualityMeasurement[]>([]);
  const [weatherData, setWeatherData] = useState<AirQualityMeasurement[]>([]);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [qualitySummaries, setQualitySummaries] = useState<DataQualitySummary[]>([]);
  const [ingestionRuns, setIngestionRuns] = useState<IngestionRun[]>([]);
  const [rejectedRecords, setRejectedRecords] = useState<RejectedRecord[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [gold, aq, weather, pipeline, quality, ingestion, rejected] = await Promise.all([
          fetchGoldData(),
          fetchAQMeasurements(),
          fetchWeatherMeasurements(),
          fetchPipelineRuns(),
          fetchQualitySummaries(),
          fetchIngestionRuns(),
          fetchRejectedRecords(),
        ]);
        setGoldData(gold);
        setAqData(aq);
        setWeatherData(weather);
        setPipelineRuns(pipeline);
        setQualitySummaries(quality);
        setIngestionRuns(ingestion);
        setRejectedRecords(rejected);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const latestPipeline = pipelineRuns[0];
  const latestIngestion = ingestionRuns[0];
  const dataSourceLabel = latestIngestion?.data_source === 'live' ? 'LIVE API' : latestIngestion?.data_source === 'sample' ? 'SAMPLE DATA' : 'UNKNOWN';

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col fixed h-screen z-10">
        <div className="p-5 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Wind className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-white leading-tight">Air Quality Index</h1>
              <p className="text-xs text-slate-400">Analysis & Prediction</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => setActiveView(item.key)}
              className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
                activeView === item.key
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'hover:bg-slate-800 text-slate-400'
              }`}
            >
              <div className="mt-0.5">{item.icon}</div>
              <div>
                <div className="text-sm font-medium">{item.label}</div>
                <div className={`text-xs ${activeView === item.key ? 'text-blue-200' : 'text-slate-500'}`}>{item.desc}</div>
              </div>
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-700 space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <GitBranch className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-slate-500">Part 1: Data Pipeline</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${latestPipeline?.status === 'success' ? 'bg-green-500' : 'bg-amber-500'} animate-pulse`} />
            <span className="text-xs text-slate-400">Pipeline: {latestPipeline?.status ?? 'idle'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${dataSourceLabel === 'LIVE API' ? 'bg-blue-500' : 'bg-amber-500'}`} />
            <span className="text-xs text-slate-400">Source: {dataSourceLabel}</span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-64 p-6 lg:p-8">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-800">
              {NAV_ITEMS.find((n) => n.key === activeView)?.label}
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              {NAV_ITEMS.find((n) => n.key === activeView)?.desc}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm">
              <div className={`w-2 h-2 rounded-full ${dataSourceLabel === 'LIVE API' ? 'bg-blue-500' : 'bg-amber-500'}`} />
              <span className="text-xs font-medium text-slate-600">{dataSourceLabel}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm">
              <div className={`w-2 h-2 rounded-full ${latestPipeline?.status === 'success' ? 'bg-green-500' : 'bg-amber-500'} animate-pulse`} />
              <span className="text-xs font-medium text-slate-600">{latestPipeline?.status ?? 'idle'}</span>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <div className="flex items-center gap-2 text-red-700">
              <span className="font-medium">Error loading data:</span>
              <span className="text-sm">{error}</span>
            </div>
          </div>
        )}

        {/* Views */}
        {activeView === 'overview' && (
          <OverviewView goldData={goldData} pipelineRuns={pipelineRuns} ingestionRuns={ingestionRuns} loading={loading} />
        )}
        {activeView === 'trend' && (
          <TrendView goldData={goldData} loading={loading} />
        )}
        {activeView === 'pollutant' && (
          <PollutantView aqData={aqData} loading={loading} />
        )}
        {activeView === 'comparison' && (
          <ComparisonView goldData={goldData} loading={loading} />
        )}
        {activeView === 'weather' && (
          <WeatherView goldData={goldData} loading={loading} />
        )}
        {activeView === 'pipeline' && (
          <PipelineView
            pipelineRuns={pipelineRuns}
            qualitySummaries={qualitySummaries}
            ingestionRuns={ingestionRuns}
            rejectedRecords={rejectedRecords}
            loading={loading}
          />
        )}

        {/* Footer */}
        <div className="mt-12 pt-6 border-t border-slate-200 flex items-center justify-between text-xs text-slate-400">
          <span>Air Quality Index Pipeline — Data Engineering & MLOps Course Project</span>
          <span>Part 1 of 2 — Data Pipeline | Part 2: MLOps / AQI Prediction (planned)</span>
        </div>
      </main>
    </div>
  );
}
