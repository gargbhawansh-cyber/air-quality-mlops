"""
Aggregate module — builds the gold analytical data mart.
Creates daily aggregations with AQI calculation and AQI category.
"""
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import requests
from config import API_BASE, get_headers


# AQI breakpoints based on Indian CPCB sub-index methodology
# Using PM2.5 as the primary pollutant for AQI calculation
# Reference: CPCB Air Quality Index (AQI) standards
AQI_BREAKPOINTS = [
    (0, 30, "Good"),
    (31, 60, "Satisfactory"),
    (61, 90, "Moderate"),
    (91, 120, "Poor"),
    (121, 250, "Very Poor"),
    (251, 500, "Severe"),
]

# PM2.5 concentration -> AQI sub-index breakpoints (ug/m3)
PM25_AQI_BREAKPOINTS = [
    (0, 30, 0, 50),
    (31, 60, 51, 100),
    (61, 90, 101, 150),
    (91, 120, 151, 200),
    (121, 250, 201, 300),
    (251, 500, 301, 500),
]

# PM10 concentration -> AQI sub-index breakpoints (ug/m3)
PM10_AQI_BREAKPOINTS = [
    (0, 50, 0, 50),
    (51, 100, 51, 100),
    (101, 250, 101, 150),
    (251, 350, 151, 200),
    (351, 430, 201, 300),
    (431, 560, 301, 500),
]

# NO2 concentration -> AQI sub-index breakpoints (ug/m3)
NO2_AQI_BREAKPOINTS = [
    (0, 40, 0, 50),
    (41, 80, 51, 100),
    (81, 180, 101, 150),
    (181, 280, 151, 200),
    (281, 400, 201, 300),
    (401, 600, 301, 500),
]

# SO2 concentration -> AQI sub-index breakpoints (ug/m3)
SO2_AQI_BREAKPOINTS = [
    (0, 40, 0, 50),
    (41, 80, 51, 100),
    (81, 380, 101, 150),
    (381, 800, 151, 200),
    (801, 1600, 201, 300),
    (1601, 2400, 301, 500),
]

# CO concentration -> AQI sub-index breakpoints (mg/m3)
CO_AQI_BREAKPOINTS = [
    (0, 1.0, 0, 50),
    (1.1, 2.0, 51, 100),
    (2.1, 10, 101, 150),
    (11, 17, 151, 200),
    (18, 34, 201, 300),
    (35, 50, 301, 500),
]

# O3 concentration -> AQI sub-index breakpoints (ug/m3)
O3_AQI_BREAKPOINTS = [
    (0, 50, 0, 50),
    (51, 100, 51, 100),
    (101, 168, 101, 150),
    (169, 208, 151, 200),
    (209, 748, 201, 300),
    (749, 1000, 301, 500),
]

POLLUTANT_BREAKPOINTS = {
    "pm25": PM25_AQI_BREAKPOINTS,
    "pm10": PM10_AQI_BREAKPOINTS,
    "no2": NO2_AQI_BREAKPOINTS,
    "so2": SO2_AQI_BREAKPOINTS,
    "co": CO_AQI_BREAKPOINTS,
    "o3": O3_AQI_BREAKPOINTS,
}


def calculate_sub_index(pollutant, concentration):
    """Calculate the AQI sub-index for a single pollutant using linear interpolation."""
    if concentration is None or concentration < 0:
        return None

    breakpoints = POLLUTANT_BREAKPOINTS.get(pollutant)
    if not breakpoints:
        return None

    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= concentration <= c_high:
            # Linear interpolation
            aqi = round(((i_high - i_low) / (c_high - c_low)) * (concentration - c_low) + i_low)
            return aqi
    # Above highest breakpoint
    return 500


def calculate_aqi(pollutant_averages):
    """
    Calculate overall AQI as the maximum sub-index across all pollutants.
    This follows CPCB methodology where AQI = max of all sub-indices.
    """
    sub_indices = {}
    for pollutant, avg_value in pollutant_averages.items():
        if avg_value is not None:
            si = calculate_sub_index(pollutant, avg_value)
            if si is not None:
                sub_indices[pollutant] = si

    if not sub_indices:
        return None, None

    aqi = max(sub_indices.values())
    category = get_aqi_category(aqi)
    return aqi, category


def get_aqi_category(aqi):
    """Map an AQI value to its category label."""
    if aqi is None:
        return None
    for low, high, category in AQI_BREAKPOINTS:
        if low <= aqi <= high:
            return category
    return "Severe"


def fetch_air_quality_data():
    """Fetch air quality measurements from the database for aggregation."""
    try:
        resp = requests.get(
            f"{API_BASE}/air_quality_measurements?select=station_id,station_name,city,measurement_time,pollutant,value,unit,latitude,longitude",
            headers=get_headers(),
            timeout=30,
        )
        if resp.ok:
            return resp.json()
        return []
    except Exception as e:
        print(f"[AGGREGATE] Error fetching AQ data: {e}")
        return []


def fetch_weather_data():
    """Fetch weather measurements for enrichment."""
    try:
        resp = requests.get(
            f"{API_BASE}/weather_measurements?select=location_name,measurement_time,temperature,humidity,precipitation,wind_speed",
            headers=get_headers(),
            timeout=30,
        )
        if resp.ok:
            return resp.json()
        return []
    except Exception as e:
        print(f"[AGGREGATE] Error fetching weather data: {e}")
        return []


def build_gold_table(pipeline_run_id=None):
    """
    Build the gold_air_quality_daily analytical table.
    Groups by date + station, computes daily averages, calculates AQI.
    """
    print("[AGGREGATE] Fetching air quality data...")
    aq_data = fetch_air_quality_data()
    print(f"[AGGREGATE] Fetched {len(aq_data)} air quality records")

    print("[AGGREGATE] Fetching weather data...")
    weather_data = fetch_weather_data()
    print(f"[AGGREGATE] Fetched {len(weather_data)} weather records")

    if not aq_data:
        print("[AGGREGATE] No air quality data to aggregate")
        return []

    # Group AQ data by (date, station_id, city)
    grouped = defaultdict(lambda: {
        "station_name": "",
        "city": "",
        "pollutants": defaultdict(list),
        "lat": None,
        "lon": None,
    })

    for rec in aq_data:
        ts = rec.get("measurement_time", "")
        if not ts:
            continue
        date_str = ts[:10]  # YYYY-MM-DD
        station_id = rec.get("station_id", "")
        key = (date_str, station_id)

        grouped[key]["station_name"] = rec.get("station_name", "")
        grouped[key]["city"] = rec.get("city", "")
        grouped[key]["lat"] = rec.get("latitude")
        grouped[key]["lon"] = rec.get("longitude")
        pollutant = rec.get("pollutant", "").lower()
        value = rec.get("value")
        if value is not None:
            grouped[key]["pollutants"][pollutant].append(float(value))

    # Build weather lookup by (city, date)
    weather_by_city_date = defaultdict(lambda: {"temp": [], "hum": [], "rain": [], "wind": []})
    for w in weather_data:
        ts = w.get("measurement_time", "")
        if not ts:
            continue
        date_str = ts[:10]
        city = w.get("location_name", "")
        if w.get("temperature") is not None:
            weather_by_city_date[(city, date_str)]["temp"].append(float(w["temperature"]))
        if w.get("humidity") is not None:
            weather_by_city_date[(city, date_str)]["hum"].append(float(w["humidity"]))
        if w.get("precipitation") is not None:
            weather_by_city_date[(city, date_str)]["rain"].append(float(w["precipitation"]))
        if w.get("wind_speed") is not None:
            weather_by_city_date[(city, date_str)]["wind"].append(float(w["wind_speed"]))

    # Build gold records
    gold_records = []
    for (date_str, station_id), data in grouped.items():
        pollutant_avgs = {}
        for pollutant in ["pm25", "pm10", "no2", "so2", "co", "o3"]:
            values = data["pollutants"].get(pollutant, [])
            if values:
                pollutant_avgs[pollutant] = round(sum(values) / len(values), 2)
            else:
                pollutant_avgs[pollutant] = None

        # Weather averages
        weather = weather_by_city_date.get((data["city"], date_str), {})
        avg_temp = round(sum(weather["temp"]) / len(weather["temp"]), 2) if weather["temp"] else None
        avg_hum = round(sum(weather["hum"]) / len(weather["hum"]), 2) if weather["hum"] else None
        avg_rain = round(sum(weather["rain"]) / len(weather["rain"]), 2) if weather["rain"] else None
        avg_wind = round(sum(weather["wind"]) / len(weather["wind"]), 2) if weather["wind"] else None

        # Calculate AQI
        aqi, aqi_category = calculate_aqi(pollutant_avgs)

        total_obs = sum(len(v) for v in data["pollutants"].values())

        gold_records.append({
            "date": date_str,
            "city": data["city"],
            "station_id": station_id,
            "station_name": data["station_name"],
            "avg_pm25": pollutant_avgs.get("pm25"),
            "avg_pm10": pollutant_avgs.get("pm10"),
            "avg_no2": pollutant_avgs.get("no2"),
            "avg_so2": pollutant_avgs.get("so2"),
            "avg_co": pollutant_avgs.get("co"),
            "avg_o3": pollutant_avgs.get("o3"),
            "avg_temperature": avg_temp,
            "avg_humidity": avg_hum,
            "avg_rainfall": avg_rain,
            "avg_wind_speed": avg_wind,
            "aqi": aqi,
            "aqi_category": aqi_category,
            "observation_count": total_obs,
            "pipeline_run_id": pipeline_run_id,
        })

    print(f"[AGGREGATE] Built {len(gold_records)} gold records")
    return gold_records
