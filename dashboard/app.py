"""
Streamlit Dashboard — Air Quality Index Analysis & Prediction
Part 1: Data Engineering Pipeline

Connected to PostgreSQL/Supabase. All values come from actual stored/processed data.

Run with:
    streamlit run dashboard/app.py
"""
import os
import sys
import requests
from datetime import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
API_BASE = f"{SUPABASE_URL}/rest/v1"
HEADERS = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}

# ---- Data fetchers ----

def fetch_table(table, limit=10000):
    try:
        resp = requests.get(f"{API_BASE}/{table}?limit={limit}", headers=HEADERS, timeout=30)
        if resp.ok:
            return resp.json()
        return []
    except Exception as e:
        st.error(f"Error fetching {table}: {e}")
        return []

def fetch_gold():
    return fetch_table("gold_air_quality_daily")

def fetch_aq():
    return fetch_table("air_quality_measurements")

def fetch_weather():
    return fetch_table("weather_measurements")

def fetch_pipeline_runs():
    return fetch_table("pipeline_runs")

def fetch_quality_summaries():
    return fetch_table("data_quality_summary")

def fetch_ingestion_runs():
    return fetch_table("ingestion_runs")

def fetch_rejected():
    return fetch_table("rejected_records")

# ---- AQI helpers ----

AQI_CATEGORIES = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
AQI_COLORS = {"Good": "#00b764", "Satisfactory": "#84cc16", "Moderate": "#eab308",
              "Poor": "#f97316", "Very Poor": "#ef4444", "Severe": "#7f1d1d"}

# ---- Page config ----

st.set_page_config(
    page_title="Air Quality Index Dashboard",
    page_icon="🌬️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; }
    .sub-header { font-size: 0.875rem; color: #64748b; margin-bottom: 1rem; }
    .kpi-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; text-align: center; }
    .kpi-value { font-size: 2rem; font-weight: 700; color: #1e293b; }
    .kpi-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
    .pipeline-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ---- Sidebar ----

st.sidebar.markdown("## 🌬️ Air Quality Index")
st.sidebar.markdown("**Analysis & Prediction**")
st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")
page = st.sidebar.radio("Select View", [
    "📊 AQI Overview",
    "📈 AQI Trend",
    "🔬 Pollutant Analysis",
    "🏙️ City / Station Comparison",
    "🌧️ Weather Impact",
    "⚙️ Pipeline Status",
    "--- Part 2: ML Prediction ---",
    "🤖 ML Prediction Dashboard",
    "📊 ML Model Metrics",
    "🔍 Feature Importance",
    "📉 Confusion Matrix",
    "🚨 Drift Monitoring",
])

st.sidebar.markdown("---")
st.sidebar.markdown("### Data Source")

# Fetch pipeline + ingestion data for sidebar
pipeline_runs = fetch_pipeline_runs()
ingestion_runs = fetch_ingestion_runs()

if pipeline_runs:
    latest = pipeline_runs[0]
    status = latest.get("status", "unknown")
    color = "#16a34a" if status == "success" else "#dc2626"
    st.sidebar.markdown(f'<span class="pipeline-badge" style="background:{color}20;color:{color}">Pipeline: {status.upper()}</span>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**Records:** {latest.get('total_records', 0):,}")
    st.sidebar.markdown(f"**Gold Records:** {latest.get('gold_records', 0):,}")

if ingestion_runs:
    src = ingestion_runs[0].get("data_source", "unknown")
    src_color = "#3b82f6" if src == "live" else "#f59e0b"
    st.sidebar.markdown(f'<span class="pipeline-badge" style="background:{src_color}20;color:{src_color}">{src.upper()}</span>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Part 1: Data Pipeline** | **Part 2: MLOps**")

# ---- Load data ----

@st.cache_data(ttl=60)
def load_data():
    return {
        "gold": pd.DataFrame(fetch_gold()),
        "aq": pd.DataFrame(fetch_aq()),
        "weather": pd.DataFrame(fetch_weather()),
        "quality": pd.DataFrame(fetch_quality_summaries()),
        "ingestion": pd.DataFrame(fetch_ingestion_runs()),
        "rejected": pd.DataFrame(fetch_rejected()),
        "pipeline": pd.DataFrame(fetch_pipeline_runs()),
    }

data = load_data()
gold_df = data["gold"]
aq_df = data["aq"]
weather_df = data["weather"]

# ---- Views ----

if page == "📊 AQI Overview":
    st.markdown('<div class="main-header">AQI Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Current air quality index and key metrics from the analytical data mart</div>', unsafe_allow_html=True)

    if gold_df.empty:
        st.warning("No data available. Run the pipeline first.")
    else:
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        latest = gold_df.sort_values("date", ascending=False).iloc[0]
        aqi_vals = gold_df["aqi"].dropna()
        stations = gold_df["station_id"].nunique()
        total_obs = gold_df["observation_count"].sum()

        with col1:
            st.metric("Latest AQI", f"{latest.get('aqi', '—')}", latest.get("aqi_category", "—"))
        with col2:
            st.metric("Average AQI", f"{aqi_vals.mean():.0f}" if not aqi_vals.empty else "—")
        with col3:
            st.metric("Highest AQI", f"{aqi_vals.max():.0f}" if not aqi_vals.empty else "—")
        with col4:
            st.metric("Total Stations", str(stations))
        with col5:
            st.metric("Total Observations", f"{total_obs:,}")
        with col6:
            st.metric("Cities", str(gold_df["city"].nunique()))

        st.markdown("---")
        st.markdown("### Latest AQI by Station")
        latest_date = gold_df["date"].max()
        latest_data = gold_df[gold_df["date"] == latest_date]
        fig = px.bar(latest_data, x="station_name", y="aqi", color="aqi_category",
                     color_discrete_map=AQI_COLORS, title=f"AQI by Station — {latest_date}",
                     labels={"station_name": "Station", "aqi": "AQI", "aqi_category": "Category"})
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(latest_data[["date", "city", "station_name", "aqi", "aqi_category",
                                   "avg_pm25", "avg_pm10", "avg_no2", "avg_so2", "avg_co", "avg_o3",
                                   "observation_count"]], use_container_width=True)

        st.markdown("---")
        st.markdown("### AQI Category Distribution")
        cat_counts = gold_df["aqi_category"].value_counts().reset_index()
        cat_counts.columns = ["category", "count"]
        cat_counts = cat_counts.sort_values("count", ascending=False)
        fig2 = px.pie(cat_counts, names="category", values="count",
                      color="category", color_discrete_map=AQI_COLORS,
                      title="Distribution of AQI Categories Across All Records")
        st.plotly_chart(fig2, use_container_width=True)

elif page == "📈 AQI Trend":
    st.markdown('<div class="main-header">AQI Trend Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Air Quality Index over time with interactive filters</div>', unsafe_allow_html=True)

    if gold_df.empty:
        st.warning("No data available.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            cities = ["All"] + sorted(gold_df["city"].unique().tolist())
            city = st.selectbox("City", cities)
        with col2:
            stations = ["All"] + sorted(gold_df["station_name"].unique().tolist())
            station = st.selectbox("Station", stations)

        filtered = gold_df.copy()
        if city != "All":
            filtered = filtered[filtered["city"] == city]
        if station != "All":
            filtered = filtered[filtered["station_name"] == station]

        fig = go.Figure()
        for cat in AQI_CATEGORIES:
            cat_data = filtered[filtered["aqi_category"] == cat]
            if not cat_data.empty:
                fig.add_trace(go.Scatter(x=cat_data["date"], y=cat_data["aqi"], mode="lines+markers",
                                         name=cat, line=dict(color=AQI_COLORS[cat])))
        fig.update_layout(title="AQI Over Time", xaxis_title="Date", yaxis_title="AQI", height=400)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(filtered[["date", "city", "station_name", "aqi", "aqi_category"]].sort_values("date", ascending=False), use_container_width=True)

elif page == "🔬 Pollutant Analysis":
    st.markdown('<div class="main-header">Pollutant Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Distribution and trends for individual pollutants</div>', unsafe_allow_html=True)

    if aq_df.empty:
        st.warning("No data available.")
    else:
        pollutants = sorted(aq_df["pollutant"].unique().tolist())
        selected = st.selectbox("Select Pollutant", pollutants)
        pollutant_data = aq_df[aq_df["pollutant"] == selected]

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Average", f"{pollutant_data['value'].mean():.2f}")
        with col2: st.metric("Minimum", f"{pollutant_data['value'].min():.2f}")
        with col3: st.metric("Maximum", f"{pollutant_data['value'].max():.2f}")
        with col4: st.metric("Measurements", f"{len(pollutant_data):,}")

        # City comparison
        city_avg = pollutant_data.groupby("city")["value"].mean().sort_values(ascending=False)
        fig = px.bar(x=city_avg.index, y=city_avg.values, title=f"Average {selected.upper()} by City",
                     labels={"x": "City", "y": f"Average {selected.upper()}"})
        st.plotly_chart(fig, use_container_width=True)

        # Time series
        if "measurement_time" in pollutant_data.columns:
            pollutant_data["hour"] = pd.to_datetime(pollutant_data["measurement_time"]).dt.strftime("%Y-%m-%d %H:00")
            hourly = pollutant_data.groupby("hour")["value"].mean().reset_index()
            fig2 = px.line(hourly, x="hour", y="value", title=f"Hourly Average {selected.upper()}")
            st.plotly_chart(fig2, use_container_width=True)

elif page == "🏙️ City / Station Comparison":
    st.markdown('<div class="main-header">City / Station Comparison</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Compare AQI levels across cities and monitoring stations</div>', unsafe_allow_html=True)

    if gold_df.empty:
        st.warning("No data available.")
    else:
        view = st.radio("Compare by", ["City", "Station"])

        if view == "City":
            city_stats = gold_df.groupby("city").agg({"aqi": ["mean", "max"], "avg_pm25": "mean", "avg_pm10": "mean"}).reset_index()
            city_stats.columns = ["city", "avg_aqi", "max_aqi", "avg_pm25", "avg_pm10"]
            fig = px.bar(city_stats, x="city", y="avg_aqi", color="city", title="Average AQI by City")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(city_stats, use_container_width=True)
        else:
            station_stats = gold_df.groupby(["station_id", "station_name", "city"]).agg({"aqi": ["mean", "max"]}).reset_index()
            station_stats.columns = ["station_id", "station_name", "city", "avg_aqi", "max_aqi"]
            fig = px.bar(station_stats, x="station_name", y="avg_aqi", color="city", title="Average AQI by Station")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(station_stats, use_container_width=True)

elif page == "🌧️ Weather Impact":
    st.markdown('<div class="main-header">Weather Impact Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Correlation between weather conditions and air quality</div>', unsafe_allow_html=True)

    if gold_df.empty:
        st.warning("No data available.")
    else:
        valid = gold_df.dropna(subset=["aqi"])

        col1, col2, col3, col4 = st.columns(4)
        for col, field, label in [(col1, "avg_temperature", "Temperature"), (col2, "avg_humidity", "Humidity"),
                                   (col3, "avg_rainfall", "Rainfall"), (col4, "avg_wind_speed", "Wind Speed")]:
            with col:
                corr = valid["aqi"].corr(valid[field]) if field in valid.columns else None
                st.metric(f"Corr: AQI vs {label}", f"{corr:.3f}" if corr is not None and not pd.isna(corr) else "—")

        if "avg_temperature" in valid.columns:
            fig = px.scatter(valid, x="avg_temperature", y="aqi", color="city",
                             title="AQI vs Temperature", labels={"avg_temperature": "Temperature (°C)"})
            st.plotly_chart(fig, use_container_width=True)

        if "avg_humidity" in valid.columns:
            fig2 = px.scatter(valid, x="avg_humidity", y="aqi", color="city",
                              title="AQI vs Humidity", labels={"avg_humidity": "Humidity (%)"})
            st.plotly_chart(fig2, use_container_width=True)

        # City weather summary
        weather_summary = valid.groupby("city").agg({
            "aqi": "mean", "avg_temperature": "mean", "avg_humidity": "mean",
            "avg_rainfall": "mean", "avg_wind_speed": "mean"
        }).reset_index()
        st.dataframe(weather_summary, use_container_width=True)

elif page == "⚙️ Pipeline Status":
    st.markdown('<div class="main-header">Data Pipeline Status</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pipeline execution metadata, data quality summaries, and ingestion logs</div>', unsafe_allow_html=True)

    pipeline_df = data["pipeline"]
    quality_df = data["quality"]
    ingestion_df = data["ingestion"]
    rejected_df = data["rejected"]

    if not pipeline_df.empty:
        latest = pipeline_df.iloc[0]
        st.markdown("### Latest Pipeline Run")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Status", latest.get("status", "—"))
        with col2: st.metric("Total Records", f"{latest.get('total_records', 0):,}")
        with col3: st.metric("Valid Records", f"{latest.get('valid_records', 0):,}")
        with col4: st.metric("Rejected", f"{latest.get('rejected_records', 0):,}")

        col5, col6, col7, col8 = st.columns(4)
        with col5: st.metric("Duplicates", latest.get("duplicate_records", 0))
        with col6: st.metric("Missing Values", latest.get("missing_value_count", 0))
        with col7: st.metric("Gold Records", latest.get("gold_records", 0))
        with col8: st.metric("Validation Failures", latest.get("validation_failures", 0))

    if not quality_df.empty:
        st.markdown("### Data Quality Summary")
        st.dataframe(quality_df[["source", "total_records", "valid_records", "rejected_records",
                                  "duplicate_records", "missing_value_count", "validation_failures",
                                  "schema_valid", "checks_passed", "checks_failed"]], use_container_width=True)

    if not ingestion_df.empty:
        st.markdown("### Ingestion Run History")
        st.dataframe(ingestion_df[["run_id", "source", "extraction_time", "status", "row_count", "data_source"]], use_container_width=True)

    if not rejected_df.empty:
        st.markdown(f"### Rejected Records ({len(rejected_df)})")
        st.dataframe(rejected_df[["rejected_id", "rejection_reason", "validation_rule", "rejected_at"]], use_container_width=True)
    else:
        st.info("No rejected records in the latest run.")

# ---- Part 2: ML Prediction Views ----

def _load_ml_models():
    """Load ML models, returning None if not trained."""
    try:
        from ml.predict import load_models
        return load_models()
    except Exception:
        return None

def _load_ml_metadata():
    """Load ML model metadata from JSON file."""
    import json
    from config import PROJECT_ROOT
    meta_path = PROJECT_ROOT / "models" / "model_metadata.json"
    if meta_path.exists():
        with open(str(meta_path)) as f:
            return json.load(f)
    return None

def _load_drift_report():
    """Load the latest drift report if it exists."""
    import json
    from config import PROJECT_ROOT
    report_path = PROJECT_ROOT / "monitoring" / "drift_report.json"
    if report_path.exists():
        with open(str(report_path)) as f:
            return json.load(f)
    return None

if page == "--- Part 2: ML Prediction ---":
    st.markdown('<div class="main-header">Part 2: ML Prediction</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Next-day AQI prediction using Machine Learning</div>', unsafe_allow_html=True)
    st.info("Select a view from the sidebar under 'Part 2: ML Prediction' to explore model predictions, metrics, and monitoring.")

elif page == "🤖 ML Prediction Dashboard":
    st.markdown('<div class="main-header">ML Prediction Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Next-day AQI predictions from trained models</div>', unsafe_allow_html=True)

    ml_models = _load_ml_models()
    ml_meta = _load_ml_metadata()

    if ml_models is None:
        st.warning("Models not trained yet. Run `python -m ml.train` to train models.")
    elif gold_df.empty:
        st.warning("No gold table data available.")
    else:
        from ml.predict import predict_batch, get_feature_importance
        from ml.features import build_feature_frame, FEATURE_COLUMNS
        import numpy as np

        reg_model, clf_model, feature_cols, metadata = ml_models

        # Build features from gold data
        rows = gold_df.to_dict("records")
        feature_df, _ = build_feature_frame(rows)

        if feature_df.empty:
            st.warning("Not enough data to generate predictions (need at least 2 consecutive days per station).")
        else:
            # Make predictions
            predictions = predict_batch(feature_df, feature_cols, reg_model, clf_model, metadata)
            results_df = feature_df[["date", "city", "station_id", "station_name", "aqi", "aqi_category"]].copy()
            results_df["predicted_aqi"] = predictions["predicted_aqi"].values
            results_df["predicted_category"] = predictions["predicted_aqi_category"].values
            results_df["actual_next_day_aqi"] = feature_df["next_day_aqi"].values
            results_df["actual_next_day_category"] = feature_df["next_day_aqi_category"].values

            st.markdown("### Predictions vs Actual")
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Total Predictions", str(len(results_df)))
            with col2: st.metric("Regression Model", metadata.get("regression_model", "—"))
            with col3: st.metric("Classification Model", metadata.get("classification_model", "—"))

            # Actual vs Predicted scatter
            fig = px.scatter(
                results_df, x="actual_next_day_aqi", y="predicted_aqi",
                color="city", title="Actual vs Predicted Next-Day AQI",
                labels={"actual_next_day_aqi": "Actual AQI", "predicted_aqi": "Predicted AQI"},
                hover_data=["station_name", "date"],
            )
            fig.add_trace(go.Scatter(
                x=[results_df["actual_next_day_aqi"].min(), results_df["actual_next_day_aqi"].max()],
                y=[results_df["actual_next_day_aqi"].min(), results_df["actual_next_day_aqi"].max()],
                mode="lines", name="Perfect Prediction", line=dict(dash="dash", color="gray"),
            ))
            st.plotly_chart(fig, use_container_width=True)

            # Predictions table
            st.dataframe(results_df[["date", "city", "station_name", "aqi",
                                     "actual_next_day_aqi", "actual_next_day_category",
                                     "predicted_aqi", "predicted_category"]].sort_values("date", ascending=False),
                         use_container_width=True)

            # Latest predictions
            st.markdown("### Latest Predictions (Most Recent Date)")
            latest_pred = results_df.sort_values("date", ascending=False).head(10)
            col1, col2 = st.columns(2)
            with col1:
                fig2 = px.bar(latest_pred, x="station_name", y="predicted_aqi",
                              color="predicted_category", color_discrete_map=AQI_COLORS,
                              title="Predicted Next-Day AQI by Station")
                st.plotly_chart(fig2, use_container_width=True)
            with col2:
                fig3 = px.bar(latest_pred, x="station_name", y="actual_next_day_aqi",
                              color="actual_next_day_category", color_discrete_map=AQI_COLORS,
                              title="Actual Next-Day AQI by Station")
                st.plotly_chart(fig3, use_container_width=True)

elif page == "📊 ML Model Metrics":
    st.markdown('<div class="main-header">ML Model Metrics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Evaluation metrics for regression and classification models</div>', unsafe_allow_html=True)

    ml_meta = _load_ml_metadata()

    if ml_meta is None:
        st.warning("Models not trained yet. Run `python -m ml.train` to train models.")
    else:
        col1, col2 = st.columns(2)

        reg_metrics = ml_meta.get("regression_metrics", {})
        clf_metrics = ml_meta.get("classification_metrics", {})

        with col1:
            st.markdown("### Regression Metrics")
            st.metric("MAE", f"{reg_metrics.get('mae', '—')}")
            st.metric("RMSE", f"{reg_metrics.get('rmse', '—')}")
            st.metric("R2 Score", f"{reg_metrics.get('r2', '—')}")
            st.markdown(f"**Model:** {ml_meta.get('regression_model', '—')}")
            st.markdown(f"**Trained:** {ml_meta.get('trained_at', '—')[:19]}")
            st.markdown(f"**Train rows:** {ml_meta.get('n_train', '—')} | **Test rows:** {ml_meta.get('n_test', '—')}")

        with col2:
            st.markdown("### Classification Metrics")
            st.metric("Accuracy", f"{clf_metrics.get('accuracy', '—')}")
            st.metric("Precision (macro)", f"{clf_metrics.get('precision_macro', '—')}")
            st.metric("Recall (macro)", f"{clf_metrics.get('recall_macro', '—')}")
            st.metric("F1 (macro)", f"{clf_metrics.get('f1_macro', '—')}")
            st.markdown(f"**Model:** {ml_meta.get('classification_model', '—')}")
            st.markdown(f"**Labels:** {', '.join(ml_meta.get('labels', []))}")

        st.markdown("---")
        st.markdown("### Feature List")
        st.json(ml_meta.get("feature_columns", []))

elif page == "🔍 Feature Importance":
    st.markdown('<div class="main-header">Feature Importance</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Feature importance from the tree-based classification model</div>', unsafe_allow_html=True)

    ml_models = _load_ml_models()

    if ml_models is None:
        st.warning("Models not trained yet. Run `python -m ml.train` to train models.")
    else:
        from ml.predict import get_feature_importance
        reg_model, clf_model, feature_cols, metadata = ml_models

        importance_clf = get_feature_importance(clf_model, feature_cols)
        importance_reg = get_feature_importance(reg_model, feature_cols)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Classification Model")
            if importance_clf:
                imp_df = pd.DataFrame(importance_clf)
                fig = px.bar(imp_df, x="importance", y="feature", orientation="h",
                             title="Feature Importance (Random Forest Classifier)")
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Feature importance not available for this model type.")

        with col2:
            st.markdown("### Regression Model")
            if importance_reg:
                imp_df = pd.DataFrame(importance_reg)
                fig = px.bar(imp_df, x="importance", y="feature", orientation="h",
                             title="Feature Importance (Random Forest Regressor)")
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Feature importance not available for this model type.")

elif page == "📉 Confusion Matrix":
    st.markdown('<div class="main-header">Confusion Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Classification model performance by AQI category</div>', unsafe_allow_html=True)

    ml_meta = _load_ml_metadata()

    if ml_meta is None:
        st.warning("Models not trained yet. Run `python -m ml.train` to train models.")
    else:
        clf_metrics = ml_meta.get("classification_metrics", {})
        cm = clf_metrics.get("confusion_matrix")
        labels = clf_metrics.get("labels", ml_meta.get("labels", []))

        if cm and labels:
            cm_df = pd.DataFrame(cm, index=[f"Actual: {l}" for l in labels],
                                 columns=[f"Pred: {l}" for l in labels])
            st.markdown("### Confusion Matrix")
            st.dataframe(cm_df, use_container_width=True)

            fig = go.Figure(data=go.Heatmap(
                z=cm, x=[f"Pred: {l}" for l in labels], y=[f"Actual: {l}" for l in labels],
                colorscale="Blues", text=cm, texttemplate="%{text}", showscale=True,
            ))
            fig.update_layout(title="Confusion Matrix Heatmap", height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Confusion matrix not available.")

        # Classification report
        report = clf_metrics.get("classification_report")
        if report:
            st.markdown("### Classification Report")
            report_rows = []
            for label, vals in report.items():
                if isinstance(vals, dict):
                    report_rows.append({
                        "Label": label,
                        "Precision": round(vals.get("precision", 0), 4),
                        "Recall": round(vals.get("recall", 0), 4),
                        "F1": round(vals.get("f1-score", 0), 4),
                        "Support": int(vals.get("support", 0)),
                    })
            if report_rows:
                st.dataframe(pd.DataFrame(report_rows), use_container_width=True)

elif page == "🚨 Drift Monitoring":
    st.markdown('<div class="main-header">Drift Monitoring</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Data drift detection using Population Stability Index (PSI)</div>', unsafe_allow_html=True)

    report = _load_drift_report()

    if report is None:
        st.warning("No drift report found. Run `python -m ml.monitor` to generate a report.")
    else:
        overall = report.get("overall_status", "UNKNOWN")
        status_color = {"HEALTHY": "#16a34a", "MODERATE DRIFT — MONITOR": "#f59e0b",
                        "RETRAINING RECOMMENDED": "#dc2626"}.get(overall, "#6b7280")

        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Overall Status", overall)
        with col2: st.metric("Reference Rows", str(report.get("reference_rows", "—")))
        with col3: st.metric("Current Rows", str(report.get("current_rows", "—")))

        st.markdown(f'<span class="pipeline-badge" style="background:{status_color}20;color:{status_color}">{overall}</span>', unsafe_allow_html=True)

        feature_reports = report.get("feature_reports", [])
        if feature_reports:
            fr_df = pd.DataFrame(feature_reports)
            st.markdown("### Per-Feature Drift Report")
            st.dataframe(fr_df, use_container_width=True)

            # PSI bar chart
            fig = px.bar(fr_df, x="feature", y="psi", color="drift_status",
                         title="PSI by Feature",
                         color_discrete_map={"no_drift": "#16a34a", "moderate_drift": "#f59e0b",
                                             "significant_drift": "#dc2626", "no_data": "#6b7280"})
            fig.add_hline(y=0.1, line_dash="dash", line_color="orange", annotation_text="Moderate threshold")
            fig.add_hline(y=0.25, line_dash="dash", line_color="red", annotation_text="Significant threshold")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"**Generated:** {report.get('generated_at', '—')[:19]}")
        st.markdown(f"**PSI Thresholds:** No drift < {report.get('thresholds', {}).get('no_drift', 0.1)} | "
                    f"Moderate < {report.get('thresholds', {}).get('moderate_drift', 0.25)} | "
                    f"Significant >= {report.get('thresholds', {}).get('moderate_drift', 0.25)}")
