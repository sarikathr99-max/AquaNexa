import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="AquaNexa | Groundwater Intelligence",
    page_icon="💧",
    layout="wide"
)

DATA_FILE = "aquanexa_dashboard_data.csv.gz"
LEVEL_COL = "Groundwater Level Telemetry 6 Hourly (meter)"

@st.cache_data
def load_data():
    data = pd.read_csv(DATA_FILE, low_memory=False)
    data["Data Acquisition Time"] = pd.to_datetime(
        data["Data Acquisition Time"], errors="coerce"
    )
    data[LEVEL_COL] = pd.to_numeric(data[LEVEL_COL], errors="coerce")
    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")
    return data.dropna(
        subset=["Station", "Data Acquisition Time", LEVEL_COL]
    )

df = load_data()

st.title("💧 AquaNexa")
st.subheader("Groundwater Intelligence and Early-Warning System")
st.caption("Tamil Nadu | DWLR telemetry data | 2021–2025")

st.sidebar.header("Dashboard Filters")
districts = ["All districts"] + sorted(
    df["District"].dropna().astype(str).unique().tolist()
)
selected_district = st.sidebar.selectbox("District", districts)

filtered = df.copy()
if selected_district != "All districts":
    filtered = filtered[filtered["District"].astype(str) == selected_district]

stations = sorted(filtered["Station"].dropna().unique().tolist())
selected_station = st.sidebar.selectbox(
    "Station", ["All stations"] + stations
)
if selected_station != "All stations":
    filtered = filtered[filtered["Station"] == selected_station]

total_readings = len(filtered)
total_stations = filtered["Station"].nunique()
potential_anomalies = filtered["Data_Quality_Flag"].eq(
    "Potential anomaly - review required"
).sum()
extreme_readings = filtered["Data_Quality_Flag"].eq(
    "Extreme reading - review required"
).sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Readings", f"{total_readings:,}")
c2.metric("Stations", f"{total_stations:,}")
c3.metric("Potential Anomalies", f"{potential_anomalies:,}")
c4.metric("Extreme Readings", f"{extreme_readings:,}")

st.divider()

# AquaNexa Early-Warning Panel
st.subheader("🚨 Early-Warning Panel")

review_flags = [
    "Potential anomaly - review required",
    "Extreme reading - review required"
]

warning_data = filtered[
    filtered["Data_Quality_Flag"].isin(review_flags)
].copy()

if warning_data.empty:
    st.success("No readings requiring review in the selected filters.")
else:
    st.warning(
        f"{len(warning_data):,} readings require data-quality review. "
        "These flags do not confirm a groundwater emergency."
    )

    station_summary = (
        warning_data.groupby(["Station", "District"], dropna=False)
        .agg(
            Readings_Requiring_Review=("Data_Quality_Flag", "size"),
            Latest_Review_Time=("Data Acquisition Time", "max")
        )
        .reset_index()
        .sort_values("Readings_Requiring_Review", ascending=False)
    )

    st.markdown("**Stations with the most readings requiring review**")
    st.dataframe(
        station_summary.head(15),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("**Most recent readings requiring review**")
    st.dataframe(
        warning_data.sort_values(
            "Data Acquisition Time", ascending=False
        )[[
            "Station",
            "District",
            "Data Acquisition Time",
            LEVEL_COL,
            "Data_Quality_Flag"
        ]].head(20),
        use_container_width=True,
        hide_index=True
    )

st.divider()
st.subheader("Groundwater-Level Trend")

trend = filtered.sort_values("Data Acquisition Time")
if not trend.empty:
    fig = px.line(
        trend,
        x="Data Acquisition Time",
        y=LEVEL_COL,
        color="Station" if selected_station == "All stations" else None,
        title="Recorded groundwater telemetry over time",
        labels={
            "Data Acquisition Time": "Date",
            LEVEL_COL: "Recorded level (m)",
            "Station": "Station"
        }
    )
    fig.update_layout(legend_title_text="Station")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No readings match the selected filters.")

st.subheader("Data-Quality Summary")
quality = (
    filtered["Data_Quality_Flag"]
    .value_counts()
    .rename_axis("Status")
    .reset_index(name="Readings")
)

left, right = st.columns(2)

with left:
    if not quality.empty:
        fig_quality = px.pie(
            quality,
            names="Status",
            values="Readings",
            title="Distribution of data-quality flags",
            hole=0.45
        )
        st.plotly_chart(fig_quality, use_container_width=True)

with right:
    st.markdown("**Readings requiring review**")
    review = filtered[
        filtered["Data_Quality_Flag"].isin([
            "Potential anomaly - review required",
            "Extreme reading - review required"
        ])
    ]
    st.dataframe(
        review[[
            "Station", "District", "Data Acquisition Time",
            LEVEL_COL, "Data_Quality_Flag"
        ]].sort_values("Data Acquisition Time", ascending=False),
        use_container_width=True,
        hide_index=True
    )

with st.expander("Explore all filtered readings"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)

st.caption(
    "Note: Flags indicate potential data-quality anomalies, not confirmed "
    "groundwater emergencies. Interpret recorded levels using the official "
    "measurement convention."
)



# --------------------------------------------------
# AquaNexa Groundwater Monitoring Map
# --------------------------------------------------

st.divider()
st.subheader("🗺️ Groundwater Monitoring Station Map")

@st.cache_data
def load_station_map():
    return pd.read_csv("aquanexa_station_map.csv")

map_data = load_station_map()

map_data["Latitude"] = pd.to_numeric(map_data["Latitude"], errors="coerce")
map_data["Longitude"] = pd.to_numeric(map_data["Longitude"], errors="coerce")

map_data = map_data.dropna(subset=["Latitude", "Longitude"])

st.caption(
    "Select a station marker to view its latest available reading. "
    "Reading dates are shown so older measurements are not mistaken for live data."
)

import plotly.express as px

map_fig = px.scatter_map(
    map_data,
    lat="Latitude",
    lon="Longitude",
    hover_name="Station",
    hover_data={
        "District": True,
        "Data Acquisition Time": True,
        "Groundwater Level Telemetry 6 Hourly (meter)": True,
        "Data_Quality_Flag": True,
        "Readings_Requiring_Review": True,
        "Latitude": False,
        "Longitude": False
    },
    color="Data_Quality_Flag",
    zoom=6,
    center={"lat": 10.9, "lon": 78.4},
    map_style="open-street-map",
    title="Tamil Nadu Groundwater Monitoring Stations"
)

map_fig.update_layout(
    height=650,
    margin={"r": 0, "t": 50, "l": 0, "b": 0}
)

st.plotly_chart(map_fig, use_container_width=True)



# AquaNexa Groundwater Prediction Module
import joblib

st.divider()
st.subheader("🔮 Groundwater Level Prediction")

st.info(
    "Experimental prediction for Eliyarpathi using a Random Forest model. "
    "This predicts the next recorded observation, which may not be exactly "
    "six hours later. It is not an emergency warning."
)

@st.cache_resource
def load_prediction_model():
    return joblib.load("aquanexa_prediction_model.pkl")

try:
    package = load_prediction_model()
    prediction_model = package["model"]
    feature_names = package["features"]

    station_name = package["station"]
    station_history = (
        df[df["Station"] == station_name]
        .dropna(subset=["Data Acquisition Time", LEVEL_COL])
        .sort_values("Data Acquisition Time")
    )

    station_history = station_history[
        station_history[LEVEL_COL].between(-100, 100)
    ].groupby("Data Acquisition Time", as_index=False)[LEVEL_COL].median()

    if len(station_history) >= 4:
        recent_levels = station_history[LEVEL_COL].tail(4).to_numpy()[::-1]
        input_data = pd.DataFrame(
            [recent_levels],
            columns=feature_names
        )

        forecast = float(prediction_model.predict(input_data)[0])

        st.markdown(f"**Selected station:** {station_name}")
        st.metric(
            "Predicted next groundwater reading",
            f"{forecast:.3f} m"
        )

        st.caption(
            f"Latest observation available: "
            f"{station_history['Data Acquisition Time'].iloc[-1]}"
        )

        st.caption(
            f"Test-set MAE: {package['mae']:.3f} m | "
            f"Test-set RMSE: {package['rmse']:.3f} m"
        )
    else:
        st.warning("Not enough historical readings to generate a prediction.")

except Exception as e:
    st.error(f"Prediction module could not load: {e}")
