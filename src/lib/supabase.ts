import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// ---- Types ----

export interface GoldAirQualityDaily {
  id: number;
  date: string;
  city: string;
  station_id: string;
  station_name: string;
  avg_pm25: number | null;
  avg_pm10: number | null;
  avg_no2: number | null;
  avg_so2: number | null;
  avg_co: number | null;
  avg_o3: number | null;
  avg_temperature: number | null;
  avg_humidity: number | null;
  avg_rainfall: number | null;
  avg_wind_speed: number | null;
  aqi: number | null;
  aqi_category: string | null;
  observation_count: number;
  pipeline_run_id: string | null;
}

export interface AirQualityMeasurement {
  measurement_id: number;
  station_id: string;
  station_name: string;
  city: string;
  country: string | null;
  latitude: number | null;
  longitude: number | null;
  measurement_time: string;
  pollutant: string;
  value: number;
  unit: string;
  source: string;
  ingestion_run_id: string;
}

export interface WeatherMeasurement {
  weather_id: number;
  location_name: string;
  latitude: number;
  longitude: number;
  measurement_time: string;
  temperature: number | null;
  humidity: number | null;
  precipitation: number | null;
  wind_speed: number | null;
  wind_direction: number | null;
  source: string;
  ingestion_run_id: string;
}

export interface IngestionRun {
  run_id: string;
  source: string;
  extraction_time: string;
  status: string;
  row_count: number;
  endpoint: string | null;
  error_message: string | null;
  data_source: string;
}

export interface PipelineRun {
  run_id: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  total_records: number;
  valid_records: number;
  rejected_records: number;
  duplicate_records: number;
  missing_value_count: number;
  validation_failures: number;
  gold_records: number;
  error_message: string | null;
}

export interface DataQualitySummary {
  summary_id: number;
  pipeline_run_id: string;
  source: string;
  total_records: number;
  valid_records: number;
  rejected_records: number;
  duplicate_records: number;
  missing_value_count: number;
  validation_failures: number;
  schema_valid: boolean;
  checks_passed: number;
  checks_failed: number;
}

export interface RejectedRecord {
  rejected_id: number;
  run_id: string;
  original_record: Record<string, unknown>;
  rejection_reason: string;
  validation_rule: string | null;
  rejected_at: string;
}

// ---- API helpers ----

export async function fetchGoldData(): Promise<GoldAirQualityDaily[]> {
  const { data, error } = await supabase
    .from('gold_air_quality_daily')
    .select('*')
    .order('date', { ascending: true });
  if (error) throw error;
  return data ?? [];
}

export async function fetchAQMeasurements(): Promise<AirQualityMeasurement[]> {
  const { data, error } = await supabase
    .from('air_quality_measurements')
    .select('*')
    .order('measurement_time', { ascending: true })
    .limit(5000);
  if (error) throw error;
  return data ?? [];
}

export async function fetchWeatherMeasurements(): Promise<WeatherMeasurement[]> {
  const { data, error } = await supabase
    .from('weather_measurements')
    .select('*')
    .order('measurement_time', { ascending: true });
  if (error) throw error;
  return data ?? [];
}

export async function fetchIngestionRuns(): Promise<IngestionRun[]> {
  const { data, error } = await supabase
    .from('ingestion_runs')
    .select('*')
    .order('extraction_time', { ascending: false });
  if (error) throw error;
  return data ?? [];
}

export async function fetchPipelineRuns(): Promise<PipelineRun[]> {
  const { data, error } = await supabase
    .from('pipeline_runs')
    .select('*')
    .order('started_at', { ascending: false });
  if (error) throw error;
  return data ?? [];
}

export async function fetchQualitySummaries(): Promise<DataQualitySummary[]> {
  const { data, error } = await supabase
    .from('data_quality_summary')
    .select('*')
    .order('summary_id', { ascending: false });
  if (error) throw error;
  return data ?? [];
}

export async function fetchRejectedRecords(): Promise<RejectedRecord[]> {
  const { data, error } = await supabase
    .from('rejected_records')
    .select('*')
    .order('rejected_at', { ascending: false });
  if (error) throw error;
  return data ?? [];
}

// ---- AQI helpers ----

export const AQI_CATEGORIES: Record<string, { color: string; bg: string; label: string }> = {
  Good: { color: '#00b764', bg: '#dcfce7', label: 'Good' },
  Satisfactory: { color: '#84cc16', bg: '#ecfccb', label: 'Satisfactory' },
  Moderate: { color: '#eab308', bg: '#fef9c3', label: 'Moderate' },
  Poor: { color: '#f97316', bg: '#ffedd5', label: 'Poor' },
  'Very Poor': { color: '#ef4444', bg: '#fee2e2', label: 'Very Poor' },
  Severe: { color: '#7f1d1d', bg: '#fecaca', label: 'Severe' },
};

export function getAQIStyle(category: string | null): { color: string; bg: string; label: string } {
  if (!category) return { color: '#6b7280', bg: '#f3f4f6', label: 'Unknown' };
  return AQI_CATEGORIES[category] ?? { color: '#6b7280', bg: '#f3f4f6', label: category };
}
