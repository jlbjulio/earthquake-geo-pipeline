import os
import time

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Dashboard de Monitoreo Sismico",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a cleaner look
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        border-left: 4px solid #0d6efd;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #212529;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .st-emotion-cache-1v0mbdj {
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def fetch_data(endpoint: str, params: dict = None) -> dict:
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/v1/{endpoint}",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return {"count": 0, "results": []}


# Sidebar filters
with st.sidebar:
    st.header("Filtros")

    min_mag = st.slider("Magnitud minima", 0.0, 9.0, 1.0, 0.1)
    days_back = st.slider("Dias hacia atras", 1, 30, 7)

    st.subheader("Busqueda por radio")
    use_radius = st.checkbox("Activar busqueda radial")
    lat = st.number_input("Latitud", value=25.0, format="%.4f")
    lon = st.number_input("Longitud", value=-100.0, format="%.4f")
    dist_km = st.slider("Radio (km)", 10, 1000, 200)

    st.divider()
    if st.button("Refrescar ahora", use_container_width=True, type="primary"):
        st.rerun()

    st.caption(
        f"Datos obtenidos de USGS Earthquake Catalog via API propia con PostGIS. "
        f"Backend: {API_BASE_URL}"
    )


# Title
st.title("Dashboard de Monitoreo Sismico")
st.caption(
    "Datos en tiempo real del USGS Earthquake Catalog. "
    "Pipeline geoespacial con PostGIS, FastAPI y Streamlit."
)

# KPIs
stats = fetch_data("earthquakes/stats")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Total de Eventos</div>
            <div class="metric-value">{stats.get("total_events", "N/A")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    val = stats.get("avg_magnitude", "N/A")
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Magnitud Promedio</div>
            <div class="metric-value">{val if val is not None else "--"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    val = stats.get("max_magnitude", "N/A")
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Magnitud Maxima</div>
            <div class="metric-value">{val if val is not None else "--"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col4:
    val = stats.get("total_tsunami", "N/A")
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Eventos con Tsunami</div>
            <div class="metric-value">{val if val is not None else "--"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# Data fetching for map and table
if use_radius:
    data = fetch_data(
        "earthquakes/radius",
        {
            "lat": lat,
            "lon": lon,
            "dist_km": dist_km,
            "min_mag": min_mag,
            "limit": 500,
        },
    )
else:
    data = fetch_data(
        "earthquakes",
        {
            "min_mag": min_mag,
            "days_back": days_back,
            "limit": 500,
        },
    )

results = data.get("results", [])

# Map
st.subheader("Mapa de Eventos Sismicos")

if results:
    avg_lat = sum(r["latitude"] for r in results) / len(results)
    avg_lon = sum(r["longitude"] for r in results) / len(results)
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=3,
        tiles="CartoDB positron",
    )

    for eq in results:
        mag = eq.get("mag", 0)
        color = (
            "green" if mag < 2
            else "yellow" if mag < 4
            else "orange" if mag < 6
            else "red"
        )
        radius = max(3, min(mag * 3, 30))

        tsunami_text = "Si" if eq.get("tsunami") else "No"
        popup_html = (
            f"<b>{eq.get('place', 'Unknown')}</b><br>"
            f"Magnitud: {mag}<br>"
            f"Profundidad: {eq.get('depth', 'N/A')} km<br>"
            f"Hora: {eq.get('time', 'N/A')}<br>"
            f"Tsunami: {tsunami_text}<br>"
            f"<a href='{API_BASE_URL}/api/v1/earthquakes/{eq['usgs_id']}' "
            f"target='_blank'>Ver detalle</a>"
        )

        folium.CircleMarker(
            location=[eq["latitude"], eq["longitude"]],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(popup_html),
        ).add_to(m)

    if use_radius:
        folium.Circle(
            location=[lat, lon],
            radius=dist_km * 1000,
            color="blue",
            fill=False,
            weight=2,
            dash_array="5, 5",
        ).add_to(m)

    st_folium(m, width=None, height=500, key="main_map")
else:
    st.warning("No se encontraron eventos sismicos con los filtros actuales.")

st.divider()

# Data table
st.subheader("Ultimos Eventos")

if results:
    df = pd.DataFrame(results)
    df = df.drop(columns=["usgs_id"], errors="ignore")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["time"] = df["time"].dt.strftime("%Y-%m-%d %H:%M UTC")

    col_order = [
        "mag", "place", "time", "depth",
        "latitude", "longitude", "magType",
        "tsunami", "alert", "status",
    ]
    col_order = [c for c in col_order if c in df.columns]
    st.dataframe(df[col_order], use_container_width=True, hide_index=True)
else:
    st.info("Sin datos para mostrar.")

st.divider()

# Clusters
st.subheader("Clusters Sismicos (DBSCAN)")
cluster_data = fetch_data("earthquakes/clusters", {"radius_km": 100})
clusters = cluster_data.get("results", [])

if clusters:
    df_clusters = pd.DataFrame(clusters)
    df_clusters.columns = [
        "Cluster ID", "Latitud Centro", "Longitud Centro",
        "Conteo", "Mag Promedio", "Mag Maxima",
    ]
    st.dataframe(df_clusters, use_container_width=True, hide_index=True)
else:
    st.info("No se encontraron clusters.")

st.divider()

# Magnitude distribution chart
st.subheader("Distribucion de Magnitudes")
if results:
    df_plot = pd.DataFrame(results)
    st.bar_chart(df_plot["mag"].value_counts().sort_index())
