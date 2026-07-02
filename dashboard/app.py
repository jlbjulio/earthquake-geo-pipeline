import os
from math import pi, sqrt

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

try:
    from countryinfo import CountryInfo
except ImportError:
    CountryInfo = None

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001").rstrip("/")
API_PUBLIC_URL = os.getenv("API_PUBLIC_URL", API_BASE_URL).rstrip("/")

EXTRA_LOCATION_PRESETS = {
    "Personalizado": {"lat": 8.9824, "lon": -79.5199, "radius": 500},
    "Afganistan": {"lat": 33.9391, "lon": 67.7100, "radius": 900},
    "Alaska": {"lat": 64.2008, "lon": -149.4937, "radius": 1000},
    "Alemania": {"lat": 51.1657, "lon": 10.4515, "radius": 650},
    "Argentina": {"lat": -38.4161, "lon": -63.6167, "radius": 1400},
    "Australia": {"lat": -25.2744, "lon": 133.7751, "radius": 1800},
    "Bolivia": {"lat": -16.2902, "lon": -63.5887, "radius": 900},
    "Brasil": {"lat": -14.2350, "lon": -51.9253, "radius": 1800},
    "California": {"lat": 36.7783, "lon": -119.4179, "radius": 700},
    "Canada": {"lat": 56.1304, "lon": -106.3468, "radius": 1800},
    "Chile": {"lat": -33.4489, "lon": -70.6693, "radius": 900},
    "China": {"lat": 35.8617, "lon": 104.1954, "radius": 1800},
    "Colombia": {"lat": 4.5709, "lon": -74.2973, "radius": 850},
    "Costa Rica": {"lat": 9.7489, "lon": -83.7534, "radius": 500},
    "Ecuador": {"lat": -1.8312, "lon": -78.1834, "radius": 650},
    "El Salvador": {"lat": 13.7942, "lon": -88.8965, "radius": 450},
    "Espana": {"lat": 40.4637, "lon": -3.7492, "radius": 750},
    "Estados Unidos": {"lat": 39.8283, "lon": -98.5795, "radius": 2000},
    "Filipinas": {"lat": 12.8797, "lon": 121.7740, "radius": 900},
    "Francia": {"lat": 46.2276, "lon": 2.2137, "radius": 750},
    "Grecia": {"lat": 39.0742, "lon": 21.8243, "radius": 650},
    "Guatemala": {"lat": 15.7835, "lon": -90.2308, "radius": 550},
    "Haiti": {"lat": 18.9712, "lon": -72.2852, "radius": 450},
    "Honduras": {"lat": 15.2000, "lon": -86.2419, "radius": 550},
    "India": {"lat": 20.5937, "lon": 78.9629, "radius": 1700},
    "Indonesia": {"lat": -0.7893, "lon": 113.9213, "radius": 1700},
    "Iran": {"lat": 32.4279, "lon": 53.6880, "radius": 1100},
    "Italia": {"lat": 41.8719, "lon": 12.5674, "radius": 650},
    "Jamaica": {"lat": 18.1096, "lon": -77.2975, "radius": 350},
    "Japon": {"lat": 38.5000, "lon": 142.0000, "radius": 900},
    "Mexico": {"lat": 19.4326, "lon": -99.1332, "radius": 900},
    "Nepal": {"lat": 28.3949, "lon": 84.1240, "radius": 650},
    "Nicaragua": {"lat": 12.8654, "lon": -85.2072, "radius": 500},
    "Nueva Zelanda": {"lat": -40.9006, "lon": 174.8860, "radius": 850},
    "Pakistan": {"lat": 30.3753, "lon": 69.3451, "radius": 1000},
    "Panama": {"lat": 8.9824, "lon": -79.5199, "radius": 600},
    "Papua Nueva Guinea": {"lat": -6.3150, "lon": 143.9555, "radius": 900},
    "Peru": {"lat": -9.1900, "lon": -75.0152, "radius": 950},
    "Puerto Rico": {"lat": 18.2208, "lon": -66.5901, "radius": 350},
    "Republica Dominicana": {"lat": 18.7357, "lon": -70.1627, "radius": 350},
    "Rusia": {"lat": 61.5240, "lon": 105.3188, "radius": 2200},
    "Taiwan": {"lat": 23.6978, "lon": 120.9605, "radius": 450},
    "Turquia": {"lat": 38.9637, "lon": 35.2433, "radius": 900},
    "Venezuela": {"lat": 6.4238, "lon": -66.5897, "radius": 900},
}

MAP_STYLES = {
    "Claro detallado": {
        "tiles": "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
    },
    "Claro simple": {
        "tiles": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        "attr": "&copy; OpenStreetMap contributors &copy; CARTO",
    },
    "OpenStreetMap": {
        "tiles": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attr": "&copy; OpenStreetMap contributors",
    },
}


def estimate_country_radius(area):
    try:
        area = float(area or 0)
    except (TypeError, ValueError):
        area = 0
    if area <= 0:
        return 700
    return int(max(250, min(2500, sqrt(area / pi) * 1.35)))


def build_location_presets():
    presets = dict(EXTRA_LOCATION_PRESETS)
    if CountryInfo is not None:
        try:
            for name, info in CountryInfo.all().items():
                latlng = info.get("latlng") or []
                if len(latlng) >= 2 and name not in presets:
                    presets[name] = {
                        "lat": float(latlng[0]),
                        "lon": float(latlng[1]),
                        "radius": estimate_country_radius(info.get("area")),
                    }
        except Exception:
            pass

    first = {"Personalizado": presets["Personalizado"]}
    rest = {
        name: presets[name]
        for name in sorted(presets)
        if name != "Personalizado"
    }
    return {**first, **rest}


LOCATION_PRESETS = build_location_presets()

MAG_COLORS = {
    "low": "#2f855a",
    "mid": "#c98900",
    "high": "#d65a31",
    "severe": "#b42318",
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
        --ink: #24150f;
        --muted: #6d5548;
        --panel: #fff8f0;
        --panel-strong: #ffffff;
        --line: #dfc9b7;
        --app-bg: #2b1712;
        --main-bg: #f4e8dc;
        --sidebar: #24120e;
        --sidebar-soft: #3a211b;
        --sidebar-line: #70483a;
        --sidebar-text: #fff8f2;
        --sidebar-muted: #ead6c9;
        --primary: #7a3f2a;
        --primary-dark: #4b2419;
        --accent: #a85b36;
        --focus: #8d4c31;
    }
    .stApp {
        background: var(--app-bg);
        color: var(--ink);
        font-family: "Segoe UI", Arial, sans-serif;
        text-rendering: optimizeLegibility;
    }
    .stApp *,
    div[data-baseweb="popover"] *,
    div[data-baseweb="tooltip"] * {
        text-shadow: none !important;
        filter: none !important;
        opacity: 1 !important;
    }
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: var(--app-bg);
    }
    .block-container {
        background: var(--main-bg);
        border: 1px solid #6b4539;
        border-radius: 10px;
        margin-top: 1rem;
        margin-bottom: 1rem;
        padding: 1.25rem 1.45rem 2rem 1.45rem;
        max-width: 1440px;
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22);
    }
    section[data-testid="stSidebar"] {
        background: var(--sidebar);
        border-right: 1px solid var(--sidebar-line);
    }
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] * {
        color: var(--sidebar-text) !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: var(--sidebar-line);
    }
    h1, h2, h3 {
        color: var(--ink);
        letter-spacing: 0;
    }
    p, label, span, div[data-testid="stMarkdownContainer"] {
        color: var(--ink);
    }
    [data-testid="stCaptionContainer"] {
        color: var(--muted);
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="input"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="base-input"] {
        background: #fffaf7 !important;
        border-color: var(--sidebar-line) !important;
        border-width: 1px !important;
        box-shadow: none !important;
        min-height: 2.65rem !important;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div,
    section[data-testid="stSidebar"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] div[data-baseweb="base-input"] * {
        color: var(--ink) !important;
        font-family: "Segoe UI", Arial, sans-serif !important;
        font-size: 0.98rem !important;
        font-weight: 400 !important;
        letter-spacing: 0 !important;
        line-height: 1.35 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
        color: var(--sidebar-muted) !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        background: var(--sidebar-soft);
        border-radius: 8px;
        padding: 0.15rem 0.35rem;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label * {
        color: var(--sidebar-text) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stTooltipHoverTarget"] *,
    section[data-testid="stSidebar"] [data-testid="stTooltipHoverTarget"] {
        color: var(--sidebar-text) !important;
    }
    div[data-baseweb="popover"],
    div[data-baseweb="tooltip"] {
        background: #fff8f0 !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        box-shadow: 0 6px 14px rgba(36, 21, 15, 0.18) !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        filter: none !important;
        opacity: 1 !important;
    }
    div[data-baseweb="popover"] > div,
    div[data-baseweb="tooltip"] > div {
        background: #fffaf7 !important;
        filter: none !important;
        opacity: 1 !important;
    }
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] [role="listbox"],
    div[data-baseweb="popover"] [role="option"] {
        background: #fffaf7 !important;
        color: var(--ink) !important;
        font-family: "Segoe UI", Arial, sans-serif !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
        letter-spacing: 0 !important;
        line-height: 1.35 !important;
        min-height: 2.45rem !important;
        text-rendering: optimizeLegibility !important;
        -webkit-font-smoothing: auto !important;
    }
    div[data-baseweb="popover"] [role="option"]:hover,
    div[data-baseweb="popover"] [aria-selected="true"] {
        background: #f0d9c7 !important;
        color: var(--ink) !important;
    }
    div[data-baseweb="popover"] *,
    div[data-baseweb="tooltip"] *,
    [role="tooltip"],
    [role="tooltip"] * {
        color: var(--ink) !important;
    }
    div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.95rem 1rem;
        box-shadow: 0 1px 2px rgba(17, 24, 39, 0.05);
    }
    div[data-testid="stMetricValue"] {
        color: var(--ink);
        font-size: 1.6rem;
        line-height: 1.15;
    }
    div[data-testid="stMetricLabel"] {
        color: var(--muted);
    }
    .hero {
        background: #fff8f0;
        color: var(--ink);
        border: 1px solid var(--line);
        border-left: 6px solid var(--primary);
        border-radius: 8px;
        padding: 1.1rem 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.06);
    }
    .hero h1 {
        color: var(--primary-dark);
        margin: 0 0 0.25rem 0;
        font-size: 1.85rem;
    }
    .hero p {
        margin: 0;
        color: var(--muted);
        font-size: 1rem;
    }
    .status-pill {
        display: inline-block;
        padding: 0.32rem 0.65rem;
        border-radius: 999px;
        background: #e7f6f2;
        color: #17634f;
        border: 1px solid #a8d8cc;
        font-weight: 700;
        font-size: 0.82rem;
    }
    .info-strip {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.65rem;
        background: #fff8f0;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.7rem 0.85rem;
        margin: 0.35rem 0 1rem 0;
        color: var(--muted);
        box-shadow: 0 1px 2px rgba(17, 24, 39, 0.04);
    }
    .info-strip strong {
        color: var(--ink);
    }
    .legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 0.2rem 0 0.75rem 0;
    }
    .legend span {
        border: 1px solid var(--line);
        background: #fff8f0;
        border-radius: 999px;
        padding: 0.25rem 0.6rem;
        color: var(--ink);
        font-size: 0.86rem;
        box-shadow: 0 1px 2px rgba(17, 24, 39, 0.04);
    }
    .dot {
        display: inline-block;
        width: 0.65rem;
        height: 0.65rem;
        border-radius: 50%;
        margin-right: 0.35rem;
        vertical-align: -0.05rem;
    }
    button[kind="primary"] {
        background: var(--primary) !important;
        border-color: var(--primary) !important;
        color: #ffffff !important;
    }
    div[data-baseweb="tab-list"] {
        gap: 0.25rem;
    }
    button[data-baseweb="tab"] {
        background: #fff8f0;
        border: 1px solid var(--line);
        border-radius: 10px;
        color: var(--ink);
        min-height: 3rem;
        padding: 0.7rem 1.25rem;
        margin-right: 0.35rem;
        box-shadow: 0 1px 2px rgba(36, 21, 15, 0.08);
        font-size: 1rem;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--primary-dark);
        background: #f0d9c7;
        border-color: #9b6a54;
        font-weight: 700;
        box-shadow: inset 0 0 0 1px #9b6a54, 0 2px 4px rgba(36, 21, 15, 0.12);
    }
    button[data-baseweb="tab"] p {
        font-size: 1rem;
        font-weight: 700;
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"],
    iframe {
        background: #ffffff;
        border-radius: 8px;
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


def average_depth(rows):
    depths = [
        float(row["depth"])
        for row in rows
        if row.get("depth") is not None and pd.notna(row.get("depth"))
    ]
    if not depths:
        return None
    return sum(depths) / len(depths)


@st.cache_data(ttl=10, show_spinner=False)
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


def build_map(rows, use_radius, lat, lon, dist_km, map_style):
    if rows:
        avg_lat = sum(float(r["latitude"]) for r in rows) / len(rows)
        avg_lon = sum(float(r["longitude"]) for r in rows) / len(rows)
        location = [avg_lat, avg_lon]
        zoom_start = 3 if not use_radius else 5
    else:
        location = [lat, lon]
        zoom_start = 4

    fmap = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    style = MAP_STYLES.get(map_style, MAP_STYLES["Claro detallado"])
    folium.TileLayer(
        tiles=style["tiles"],
        attr=style["attr"],
        name=map_style,
        detect_retina=True,
    ).add_to(fmap)

    for eq in rows:
        mag = float(eq.get("mag") or 0)
        color = magnitude_color(mag)
        radius = max(4, min(6 + mag * 2.2, 24))
        detail_url = f"{API_PUBLIC_URL}/api/v1/earthquakes/{eq['usgs_id']}"
        popup_html = (
            f"<b>{eq.get('place', 'Unknown')}</b><br>"
            f"Magnitud: {mag}<br>"
            f"Categoria: {magnitude_label(mag)}<br>"
            f"Profundidad: {eq.get('depth', 'N/A')} km<br>"
            f"Hora: {format_time(eq.get('time'))}<br>"
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
        "Que quieres explorar?",
        ["Eventos recientes", "Cerca de una zona"],
        horizontal=True,
    )
    use_radius = view_mode == "Cerca de una zona"

    min_mag, max_mag = st.slider(
        "Magnitud que quieres ver",
        min_value=0.0,
        max_value=9.0,
        value=(1.0, 7.5),
        step=0.1,
    )

    days_back = st.slider(
        "Periodo de tiempo",
        1,
        30,
        7,
    )
    st.caption("Cuantos dias recientes quieres consultar.")
    limit = st.slider(
        "Cantidad maxima en pantalla",
        50,
        1000,
        500,
        step=50,
    )
    st.caption("Solo limita cuantos sismos se dibujan en el mapa y la tabla. La base puede tener muchos mas.")

    lat = LOCATION_PRESETS["Panama"]["lat"]
    lon = LOCATION_PRESETS["Panama"]["lon"]
    dist_km = LOCATION_PRESETS["Panama"]["radius"]

    st.divider()
    if use_radius:
        st.subheader("Buscar cerca de")
        preset = st.selectbox(
            "Pais o zona",
            list(LOCATION_PRESETS.keys()),
            help="Puedes escribir dentro del selector para encontrar rapido un pais.",
        )
        preset_data = LOCATION_PRESETS[preset]

        if preset == "Personalizado":
            lat = st.number_input("Latitud", value=preset_data["lat"], format="%.4f")
            lon = st.number_input("Longitud", value=preset_data["lon"], format="%.4f")
            dist_km = st.slider("Distancia alrededor", 10, 2000, preset_data["radius"], step=10)
        else:
            lat = preset_data["lat"]
            lon = preset_data["lon"]
            dist_km = st.slider("Distancia alrededor", 10, 2000, preset_data["radius"], step=10)
        st.caption("Escribe en el selector para buscar un pais. Si no aparece, usa Personalizado y coloca coordenadas.")
    else:
        st.caption("Eventos recientes muestra sismos globales. Usa Cerca de una zona para buscar por ubicacion.")

    st.divider()
    map_style = st.selectbox(
        "Tipo de mapa",
        list(MAP_STYLES.keys()),
    )

    refresh = st.button("Actualizar datos", width="stretch", type="primary")
    if refresh:
        st.rerun()

    st.caption("Fuente: USGS Earthquake Catalog")
    with st.expander("Guia rapida"):
        st.write("1. Usa Eventos recientes para ver sismos globales.")
        st.write("2. Usa Cerca de una zona para buscar alrededor de un pais o escribir sus coordenadas.")
        st.write("3. Ajusta la magnitud para ocultar eventos muy pequenos.")
        st.write("4. Cantidad maxima en pantalla no borra datos; solo hace mas rapido el mapa.")
        st.write("5. El mapa, la tabla y el resumen usan los mismos filtros.")

st.markdown(
    """
    <div class="hero">
        <h1>Monitor Sismico Global</h1>
        <p>Explora terremotos recientes, filtra por magnitud y busca actividad sismica cerca de una zona.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

health, health_error = safe_fetch("health")
stats, stats_error = safe_fetch("earthquakes/stats")

status_html = (
    f"<span class='status-pill'>API conectada</span>"
    if not health_error
    else "<span class='status-pill' style='background:#fff1f0;color:#9f1d1d;border-color:#f3b4ad;'>API sin conexion</span>"
)
st.markdown(
    f"""
    <div class="info-strip">
        {status_html}
        <span><strong>Ultima actualizacion:</strong> {format_time(stats.get("last_update"))}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
if health_error:
    st.error(f"No se pudo conectar con el backend: {health_error}")

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

avg_depth = average_depth(rows)

metric_cols = st.columns(4)
metric_cols[0].metric("Eventos en base", format_number(stats.get("total_events")))
metric_cols[1].metric("Eventos visibles", format_number(len(rows)))
metric_cols[2].metric("Magnitud max.", format_number(stats.get("max_magnitude")))
metric_cols[3].metric(
    "Profundidad prom.",
    f"{format_number(avg_depth)} km" if avg_depth is not None else "--",
)

tab_map, tab_table, tab_summary = st.tabs(
    ["Mapa", "Eventos", "Resumen"]
)

with tab_map:
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
    left, right = st.columns([3, 1])
    with left:
        fmap = build_map(rows, use_radius, lat, lon, dist_km, map_style)
        st_folium(fmap, width=None, height=570, key="main_map")
    with right:
        st.subheader("Vista actual")
        st.metric("Eventos visibles", len(rows))
        st.metric("Magnitud minima", f"{min_mag:.1f}")
        if use_radius:
            st.metric("Distancia", f"{dist_km:,} km")
            st.caption(f"Centro: {lat:.2f}, {lon:.2f}")
        else:
            st.metric("Periodo", f"{days_back} dias")
            st.metric("Magnitud maxima", f"{max_mag:.1f}")

        if rows:
            strongest = max(rows, key=lambda item: float(item.get("mag") or 0))
            st.divider()
            st.subheader("Evento mayor")
            st.write(strongest.get("place", "Unknown"))
            st.metric("Magnitud", format_number(strongest.get("mag")))
            st.metric("Profundidad", f"{format_number(strongest.get('depth'))} km")
            st.caption(format_time(strongest.get("time")))

with tab_table:
    if rows:
        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
        df["Hora UTC"] = df["time"].dt.strftime("%Y-%m-%d %H:%M")
        df["Categoria"] = df["mag"].apply(magnitude_label)
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
            "Alerta",
            "Estado",
            "Distancia km",
        ]
        columns = [column for column in columns if column in df.columns]
        st.dataframe(df[columns], width="stretch", hide_index=True)
    else:
        st.info("No hay eventos con los filtros actuales.")

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
