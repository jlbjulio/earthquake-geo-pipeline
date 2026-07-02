import os

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001").rstrip("/")
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", API_BASE_URL).rstrip("/")

LOCATION_PRESETS = {
    "Panama": {"lat": 8.9824, "lon": -79.5199, "radius": 900},
    "California": {"lat": 36.7783, "lon": -119.4179, "radius": 700},
    "Japan": {"lat": 38.5, "lon": 142.0, "radius": 900},
    "Chile": {"lat": -33.4489, "lon": -70.6693, "radius": 900},
    "Mexico": {"lat": 19.4326, "lon": -99.1332, "radius": 900},
    "Personalizado": {"lat": 8.9824, "lon": -79.5199, "radius": 500},
}

MAG_COLORS = {
    "low": "#22a06b",
    "mid": "#f2b705",
    "high": "#f97316",
    "severe": "#dc2626",
}

st.set_page_config(
    page_title="Monitor Sismico",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #16202a;
        --muted: #667085;
        --panel: #ffffff;
        --line: #dde3ea;
        --soft: #f6f8fb;
        --teal: #007c89;
        --coral: #e76f51;
        --amber: #f2b705;
        --green: #22a06b;
    }
    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 2rem;
        max-width: 1440px;
    }
    section[data-testid="stSidebar"] {
        background: #f4f7fa;
        border-right: 1px solid var(--line);
    }
    h1, h2, h3 {
        color: var(--ink);
        letter-spacing: 0;
    }
    div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    div[data-testid="stMetricValue"] {
        color: var(--ink);
        font-size: 1.7rem;
    }
    .hero {
        background: linear-gradient(135deg, #0f3d4c 0%, #167070 48%, #e76f51 120%);
        color: white;
        border-radius: 8px;
        padding: 1.15rem 1.3rem;
        margin-bottom: 1rem;
    }
    .hero h1 {
        color: white;
        margin: 0 0 0.25rem 0;
        font-size: 2rem;
    }
    .hero p {
        margin: 0;
        color: rgba(255, 255, 255, 0.86);
    }
    .status-pill {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        background: #e8f5ef;
        color: #146c43;
        border: 1px solid #b7dfca;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 0.2rem 0 0.75rem 0;
    }
    .legend span {
        border: 1px solid var(--line);
        background: white;
        border-radius: 999px;
        padding: 0.25rem 0.6rem;
        color: var(--muted);
        font-size: 0.86rem;
    }
    .dot {
        display: inline-block;
        width: 0.65rem;
        height: 0.65rem;
        border-radius: 50%;
        margin-right: 0.35rem;
        vertical-align: -0.05rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_number(value, fallback="--"):
    if value is None:
        return fallback
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def format_time(value):
    if not value:
        return "--"
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return "--"
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def magnitude_color(mag):
    mag = float(mag or 0)
    if mag < 2:
        return MAG_COLORS["low"]
    if mag < 4:
        return MAG_COLORS["mid"]
    if mag < 6:
        return MAG_COLORS["high"]
    return MAG_COLORS["severe"]


def magnitude_label(mag):
    mag = float(mag or 0)
    if mag < 2:
        return "Micro"
    if mag < 4:
        return "Leve"
    if mag < 6:
        return "Fuerte"
    return "Severo"


@st.cache_data(ttl=45, show_spinner=False)
def fetch_data(endpoint: str, params: tuple = ()) -> dict:
    query = dict(params)
    response = requests.get(
        f"{API_BASE_URL}/api/v1/{endpoint}",
        params=query,
        timeout=12,
    )
    response.raise_for_status()
    return response.json()


def safe_fetch(endpoint: str, params: dict | None = None) -> tuple[dict, str | None]:
    try:
        return fetch_data(endpoint, tuple((params or {}).items())), None
    except Exception as err:
        return {"count": 0, "results": []}, str(err)


def build_map(rows, use_radius, lat, lon, dist_km, map_tiles):
    if rows:
        avg_lat = sum(float(r["latitude"]) for r in rows) / len(rows)
        avg_lon = sum(float(r["longitude"]) for r in rows) / len(rows)
        location = [avg_lat, avg_lon]
        zoom_start = 3 if not use_radius else 5
    else:
        location = [lat, lon]
        zoom_start = 4

    fmap = folium.Map(location=location, zoom_start=zoom_start, tiles=map_tiles)

    for eq in rows:
        mag = float(eq.get("mag") or 0)
        color = magnitude_color(mag)
        radius = max(4, min(6 + mag * 2.2, 24))
        tsunami_text = "Si" if eq.get("tsunami") else "No"
        detail_url = f"{API_PUBLIC_URL}/api/v1/earthquakes/{eq['usgs_id']}"
        popup_html = (
            f"<b>{eq.get('place', 'Unknown')}</b><br>"
            f"Magnitud: {mag}<br>"
            f"Categoria: {magnitude_label(mag)}<br>"
            f"Profundidad: {eq.get('depth', 'N/A')} km<br>"
            f"Hora: {format_time(eq.get('time'))}<br>"
            f"Tsunami: {tsunami_text}<br>"
            f"<a href='{detail_url}' target='_blank'>Ver detalle API</a>"
        )

        folium.CircleMarker(
            location=[eq["latitude"], eq["longitude"]],
            radius=radius,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.72,
            popup=folium.Popup(popup_html, max_width=320),
        ).add_to(fmap)

    if use_radius:
        folium.Marker(
            location=[lat, lon],
            tooltip="Centro de busqueda",
            icon=folium.Icon(color="blue", icon="crosshairs", prefix="fa"),
        ).add_to(fmap)
        folium.Circle(
            location=[lat, lon],
            radius=dist_km * 1000,
            color="#2563eb",
            fill=True,
            fill_opacity=0.05,
            weight=2,
        ).add_to(fmap)

    return fmap


with st.sidebar:
    st.header("Panel de control")

    view_mode = st.radio(
        "Modo de busqueda",
        ["Ultimos eventos", "Por radio"],
        horizontal=True,
    )
    use_radius = view_mode == "Por radio"

    min_mag, max_mag = st.slider(
        "Rango de magnitud",
        min_value=0.0,
        max_value=9.0,
        value=(1.0, 7.5),
        step=0.1,
    )

    days_back = st.slider("Dias hacia atras", 1, 30, 7)
    limit = st.slider("Cantidad maxima", 50, 1000, 500, step=50)

    st.divider()
    st.subheader("Zona geografica")
    preset = st.selectbox("Centro", list(LOCATION_PRESETS.keys()))
    preset_data = LOCATION_PRESETS[preset]

    if preset == "Personalizado":
        lat = st.number_input("Latitud", value=preset_data["lat"], format="%.4f")
        lon = st.number_input("Longitud", value=preset_data["lon"], format="%.4f")
        dist_km = st.slider("Radio en km", 10, 2000, preset_data["radius"], step=10)
    else:
        lat = preset_data["lat"]
        lon = preset_data["lon"]
        dist_km = st.slider("Radio en km", 10, 2000, preset_data["radius"], step=10)

    st.divider()
    cluster_radius = st.slider("Radio de clusters km", 10, 300, 100, step=10)
    map_style = st.selectbox(
        "Estilo de mapa",
        ["CartoDB positron", "OpenStreetMap", "CartoDB dark_matter"],
    )

    refresh = st.button("Actualizar datos", width="stretch", type="primary")
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.caption(f"API publica: {API_PUBLIC_URL}")

st.markdown(
    """
    <div class="hero">
        <h1>Monitor Sismico Global</h1>
        <p>Eventos recientes de USGS procesados con Mage AI, PostGIS, FastAPI y Streamlit.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

health, health_error = safe_fetch("health")
stats, stats_error = safe_fetch("earthquakes/stats")

if health_error:
    st.error(f"No se pudo conectar con el backend: {health_error}")
else:
    st.markdown('<span class="status-pill">API conectada</span>', unsafe_allow_html=True)

metric_cols = st.columns(5)
metric_cols[0].metric("Eventos", format_number(stats.get("total_events")))
metric_cols[1].metric("Magnitud prom.", format_number(stats.get("avg_magnitude")))
metric_cols[2].metric("Magnitud max.", format_number(stats.get("max_magnitude")))
metric_cols[3].metric("Tsunamis", format_number(stats.get("total_tsunami")))
metric_cols[4].metric("Ultima actualizacion", format_time(stats.get("last_update")))

query_params = {
    "min_mag": min_mag,
    "limit": limit,
}
if use_radius:
    query_params.update({"lat": lat, "lon": lon, "dist_km": dist_km})
    data, data_error = safe_fetch("earthquakes/radius", query_params)
else:
    query_params.update({"max_mag": max_mag, "days_back": days_back})
    data, data_error = safe_fetch("earthquakes", query_params)

rows = [
    row for row in data.get("results", [])
    if float(row.get("mag") or 0) <= max_mag
]

if data_error:
    st.warning(f"No se pudieron cargar eventos: {data_error}")

st.markdown(
    f"""
    <div class="legend">
        <span><i class="dot" style="background:{MAG_COLORS['low']}"></i>Micro &lt; 2</span>
        <span><i class="dot" style="background:{MAG_COLORS['mid']}"></i>Leve 2-4</span>
        <span><i class="dot" style="background:{MAG_COLORS['high']}"></i>Fuerte 4-6</span>
        <span><i class="dot" style="background:{MAG_COLORS['severe']}"></i>Severo 6+</span>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_map, tab_table, tab_clusters, tab_summary = st.tabs(
    ["Mapa", "Eventos", "Clusters", "Resumen"]
)

with tab_map:
    left, right = st.columns([3, 1])
    with left:
        fmap = build_map(rows, use_radius, lat, lon, dist_km, map_style)
        st_folium(fmap, width=None, height=570, key="main_map")
    with right:
        st.subheader("Filtro activo")
        st.metric("Resultados", len(rows))
        st.metric("Magnitud minima", f"{min_mag:.1f}")
        if use_radius:
            st.metric("Radio", f"{dist_km:,} km")
            st.metric("Centro", f"{lat:.2f}, {lon:.2f}")
        else:
            st.metric("Dias", days_back)
            st.metric("Magnitud maxima", f"{max_mag:.1f}")

        if rows:
            strongest = max(rows, key=lambda item: float(item.get("mag") or 0))
            st.divider()
            st.subheader("Evento mayor")
            st.write(strongest.get("place", "Unknown"))
            st.metric("Magnitud", format_number(strongest.get("mag")))
            st.caption(format_time(strongest.get("time")))

with tab_table:
    if rows:
        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
        df["Hora UTC"] = df["time"].dt.strftime("%Y-%m-%d %H:%M")
        df["Categoria"] = df["mag"].apply(magnitude_label)
        df["Tsunami"] = df["tsunami"].apply(lambda value: "Si" if value else "No")
        if "distance_km" in df.columns:
            df["Distancia km"] = df["distance_km"]

        rename_map = {
            "mag": "Magnitud",
            "place": "Lugar",
            "depth": "Profundidad km",
            "latitude": "Latitud",
            "longitude": "Longitud",
            "magType": "Tipo",
            "alert": "Alerta",
            "status": "Estado",
        }
        df = df.rename(columns=rename_map)
        columns = [
            "Magnitud",
            "Categoria",
            "Lugar",
            "Hora UTC",
            "Profundidad km",
            "Latitud",
            "Longitud",
            "Tipo",
            "Tsunami",
            "Alerta",
            "Estado",
            "Distancia km",
        ]
        columns = [column for column in columns if column in df.columns]
        st.dataframe(df[columns], width="stretch", hide_index=True)
    else:
        st.info("No hay eventos con los filtros actuales.")

with tab_clusters:
    cluster_data, cluster_error = safe_fetch(
        "earthquakes/clusters",
        {"radius_km": cluster_radius},
    )
    clusters = cluster_data.get("results", [])
    if cluster_error:
        st.warning(f"No se pudieron cargar clusters: {cluster_error}")
    elif clusters:
        df_clusters = pd.DataFrame(clusters)
        df_clusters = df_clusters.rename(
            columns={
                "cluster_id": "Cluster",
                "centroid_lat": "Latitud centro",
                "centroid_lng": "Longitud centro",
                "earthquake_count": "Eventos",
                "avg_mag": "Magnitud prom.",
                "max_mag": "Magnitud max.",
            }
        )
        st.dataframe(df_clusters, width="stretch", hide_index=True)
        st.bar_chart(df_clusters.set_index("Cluster")["Eventos"])
    else:
        st.info("No hay clusters para el radio seleccionado.")

with tab_summary:
    if rows:
        df_plot = pd.DataFrame(rows)
        bins = [0, 2, 4, 6, 10]
        labels = ["Micro", "Leve", "Fuerte", "Severo"]
        df_plot["Categoria"] = pd.cut(
            df_plot["mag"].astype(float),
            bins=bins,
            labels=labels,
            include_lowest=True,
        )
        dist = df_plot["Categoria"].value_counts().reindex(labels, fill_value=0)
        st.subheader("Distribucion por magnitud")
        st.bar_chart(dist)

        top_places = df_plot["place"].fillna("Unknown").head(10)
        st.subheader("Eventos recientes")
        for index, place in enumerate(top_places, start=1):
            st.write(f"{index}. {place}")
    else:
        st.info("Ajusta los filtros para ver resumen.")
