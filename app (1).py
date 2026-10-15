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
