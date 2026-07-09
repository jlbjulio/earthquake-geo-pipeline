import os
from html import escape
from math import ceil, pi, sqrt

import altair as alt
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
    "Personalizado": {"lat": 8.9824, "lon": -79.5199, "radius": 600},
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

EVENT_VIEW_OPTIONS = {
    "Mas recientes": {
        "sort": "recent",
        "paged": False,
        "caption": "Ordena por fecha UTC, del evento mas nuevo al mas antiguo.",
    },
    "Mayor magnitud primero": {
        "sort": "mag_desc",
        "paged": False,
        "caption": "Muestra primero los sismos de mayor magnitud.",
    },
    "Menor magnitud primero": {
        "sort": "mag_asc",
        "paged": False,
        "caption": "Muestra primero los sismos de menor magnitud.",
    },
    "Todos los eventos": {
        "sort": "recent",
        "paged": True,
        "caption": "Recorre todo lo cargado en la base por paginas; respeta magnitud y zona seleccionada.",
    },
}

TABLE_PAGE_SIZE = 250


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
        background: var(--main-bg);
        color: var(--ink);
        font-family: "Segoe UI", Arial, sans-serif;
    }
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: var(--main-bg);
    }
    header[data-testid="stHeader"] {
        background: var(--main-bg) !important;
        color: var(--ink) !important;
        border-bottom: 1px solid var(--line) !important;
    }
    [data-testid="stDecoration"] {
        background: var(--primary) !important;
        height: 0.18rem !important;
    }
    [data-testid="stToolbar"],
    [data-testid="stToolbar"] *,
    [data-testid="stStatusWidget"],
    [data-testid="stStatusWidget"] *,
    [data-testid="stDeployButton"],
    [data-testid="stDeployButton"] *,
    [data-testid="stMainMenu"],
    [data-testid="stMainMenu"] * {
        color: var(--ink) !important;
        fill: var(--ink) !important;
        stroke: var(--ink) !important;
    }
    [data-testid="stToolbar"] button,
    [data-testid="stToolbar"] a,
    [data-testid="stDeployButton"] button,
    [data-testid="stMainMenu"] button {
        background: #fff8f0 !important;
        color: var(--ink) !important;
        border-color: var(--line) !important;
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
    [data-testid="stMain"] *,
    .block-container *,
    [data-testid="stMetric"] *,
    div[data-testid="stDataFrame"] *,
    div[data-testid="stTable"] * {
        color: var(--ink);
    }
    [data-testid="stMain"] [data-testid="stCaptionContainer"],
    [data-testid="stMain"] [data-testid="stCaptionContainer"] *,
    .block-container [data-testid="stCaptionContainer"],
    .block-container [data-testid="stCaptionContainer"] * {
        color: var(--muted) !important;
    }
    [data-testid="stMain"] .stAlert,
    [data-testid="stMain"] .stAlert *,
    .block-container .stAlert,
    .block-container .stAlert * {
        color: var(--ink) !important;
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
    section[data-testid="stSidebar"] div[data-baseweb="select"],
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
        background: #fffaf7 !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        box-shadow: 0 6px 14px rgba(36, 21, 15, 0.18) !important;
    }
    div[data-baseweb="popover"] > div,
    div[data-baseweb="tooltip"] > div {
        background: #fffaf7 !important;
    }
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] [role="listbox"],
    div[data-baseweb="popover"] [role="option"] {
        background: #fffaf7 !important;
        color: #24150f !important;
        font-family: "Segoe UI", Arial, sans-serif !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
        letter-spacing: 0 !important;
        line-height: 1.35 !important;
        min-height: 2.45rem !important;
    }
    div[data-baseweb="popover"] [role="option"]:hover,
    div[data-baseweb="popover"] [aria-selected="true"] {
        background: #f0d9c7 !important;
        color: #24150f !important;
    }
    div[data-baseweb="popover"] *,
    div[data-baseweb="tooltip"] *,
    [role="tooltip"],
    [role="tooltip"] * {
        color: #24150f !important;
    }
    div[data-baseweb="popover"] span,
    div[data-baseweb="popover"] div,
    div[data-baseweb="select"] [role="listbox"] span,
    div[data-baseweb="select"] [role="listbox"] div {
        color: #24150f !important;
        background: #fffaf7 !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="popover"] *,
    section[data-testid="stSidebar"] div[data-baseweb="select"] [role="listbox"] * {
        color: #24150f !important;
        background: #fffaf7 !important;
    }
    div[role="listbox"] > div,
    div[role="listbox"] > div > div,
    div[role="listbox"] ul,
    div[role="listbox"] li,
    div[data-baseweb="menu"] *,
    div[data-baseweb="menu"] div,
    div[data-baseweb="menu"] span {
        background: #fffaf7 !important;
        color: #24150f !important;
    }
    [role="combobox"],
    [role="combobox"] * {
        background-color: #fffaf7 !important;
        color: #24150f !important;
    }
    [role="combobox"] svg,
    [role="combobox"] svg path,
    [role="combobox"] svg polyline,
    [role="combobox"] svg polygon {
        fill: #24150f !important;
        color: #24150f !important;
        stroke: #24150f !important;
    }
    .stSelectbox svg,
    [data-baseweb="select"] svg,
    div[data-baseweb="select"] svg {
        fill: #24150f !important;
        color: #24150f !important;
    }
    [data-testid="stMain"] div[data-baseweb="select"] > div,
    [data-testid="stMain"] div[data-baseweb="input"] > div,
    [data-testid="stMain"] div[data-baseweb="base-input"],
    .block-container div[data-baseweb="select"] > div,
    .block-container div[data-baseweb="input"] > div,
    .block-container div[data-baseweb="base-input"] {
        background: #fffaf7 !important;
        border-color: var(--line) !important;
        color: var(--ink) !important;
    }
    [data-testid="stMain"] input,
    [data-testid="stMain"] textarea,
    [data-testid="stMain"] div[data-baseweb="select"] *,
    .block-container input,
    .block-container textarea,
    .block-container div[data-baseweb="select"] * {
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
    .analysis-title {
        margin: 0.3rem 0 0.85rem 0;
    }
    .analysis-title h2 {
        margin: 0;
        color: var(--primary-dark);
        font-size: 1.35rem;
    }
    .analysis-title p {
        margin: 0.25rem 0 0 0;
        color: var(--muted);
    }
    .analysis-card {
        background: #fff8f0;
        border: 1px solid var(--line);
        border-left: 5px solid var(--primary);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        min-height: 7rem;
        box-shadow: 0 1px 3px rgba(36, 21, 15, 0.06);
    }
    .analysis-card .label {
        color: var(--muted);
        font-size: 0.82rem;
        margin-bottom: 0.25rem;
    }
    .analysis-card .value {
        color: var(--ink);
        font-size: 1.32rem;
        line-height: 1.2;
        margin-bottom: 0.4rem;
    }
    .analysis-card .note {
        color: var(--muted);
        font-size: 0.9rem;
        line-height: 1.35;
    }
    .section-band {
        background: #fff8f0;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.95rem 1rem;
        margin: 0.75rem 0 1rem 0;
    }
    .section-band h3 {
        margin: 0 0 0.25rem 0;
        color: var(--primary-dark);
        font-size: 1.05rem;
    }
    .section-band p {
        margin: 0;
        color: var(--muted);
    }
    .event-row {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        background: #fff8f0;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 0.75rem 0.85rem;
        margin-bottom: 0.55rem;
    }
    .event-row .place {
        color: var(--ink);
        font-size: 0.95rem;
    }
    .event-row .meta {
        color: var(--muted);
        font-size: 0.84rem;
        margin-top: 0.25rem;
    }
    .event-row .mag {
        color: var(--primary-dark);
        font-size: 1.15rem;
        white-space: nowrap;
    }
    button[kind="primary"] {
        background: var(--primary) !important;
        border-color: var(--primary) !important;
        color: #ffffff !important;
    }
    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button,
    .block-container button:not([data-baseweb="tab"]),
    section[data-testid="stSidebar"] button {
        background: #fff8f0 !important;
        color: var(--ink) !important;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(36, 21, 15, 0.08) !important;
        font-weight: 500 !important;
    }
    div[data-testid="stButton"] button:hover,
    div[data-testid="stDownloadButton"] button:hover,
    .block-container button:not([data-baseweb="tab"]):hover,
    section[data-testid="stSidebar"] button:hover {
        background: #f0d9c7 !important;
        color: var(--primary-dark) !important;
        border-color: #9b6a54 !important;
    }
    div[data-testid="stButton"] button:disabled,
    div[data-testid="stButton"] button[disabled] {
        background: #eadccd !important;
        color: #7c6659 !important;
        border-color: #d6c0ad !important;
        opacity: 1 !important;
    }
    div[data-testid="stButton"] button[kind="primary"],
    section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {
        background: var(--primary) !important;
        border-color: var(--primary) !important;
        color: #fff8f2 !important;
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
    .table-wrap {
        max-height: 620px;
        overflow: auto;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fff8f0;
        box-shadow: 0 1px 3px rgba(36, 21, 15, 0.08);
    }
    .table-note {
        background: #fff8f0;
        border: 1px solid var(--line);
        border-left: 5px solid var(--primary);
        border-radius: 8px;
        color: var(--ink);
        padding: 0.7rem 0.85rem;
        margin: 0.4rem 0 0.75rem 0;
        line-height: 1.45;
    }
    .table-note strong {
        color: var(--primary-dark);
    }
    .events-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: #fff8f0;
        color: var(--ink);
        font-size: 0.9rem;
    }
    .events-table thead th {
        position: sticky;
        top: 0;
        z-index: 1;
        background: #7a3f2a;
        color: #fff8f2;
        border-bottom: 1px solid #5f2f20;
        padding: 0.68rem 0.75rem;
        text-align: left;
        white-space: nowrap;
        font-weight: 600;
    }
    .events-table tbody td {
        background: #fffaf7;
        color: var(--ink);
        border-bottom: 1px solid #ead6c9;
        padding: 0.58rem 0.75rem;
        vertical-align: top;
    }
    .events-table tbody tr:nth-child(even) td {
        background: #f7eadf;
    }
    .events-table tbody tr:hover td {
        background: #f0d9c7;
    }
    .events-table td:first-child,
    .events-table th:first-child {
        border-left: 0;
    }
    </style>
    <script>
    function fixSelects() {
        document.querySelectorAll('[role="combobox"]').forEach(function(el) {
            el.style.setProperty('background-color', '#fffaf7', 'important');
            el.style.setProperty('color', '#24150f', 'important');
        });
        document.querySelectorAll('[data-baseweb="select"] svg').forEach(function(s) {
            s.setAttribute('fill', '#24150f');
            s.style.setProperty('fill', '#24150f', 'important');
            s.style.setProperty('color', '#24150f', 'important');
            if (s.parentElement) {
                s.parentElement.style.setProperty('color', '#24150f', 'important');
            }
        });
        document.querySelectorAll('.stSelectbox svg').forEach(function(s) {
            s.setAttribute('fill', '#24150f');
            s.style.setProperty('fill', '#24150f', 'important');
        });
    }
    document.addEventListener('DOMContentLoaded', fixSelects);
    setTimeout(fixSelects, 100);
    setTimeout(fixSelects, 500);
    setTimeout(fixSelects, 1500);
    </script>
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
    if value is None or value == "":
        return "--"
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return "--"
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def format_period_label(use_all_time, days_back):
    return "Todo lo cargado" if use_all_time else f"Ultimos {days_back} dias"


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


def build_event_params(
    min_mag,
    max_mag,
    days_back,
    use_all_time,
    limit,
    sort,
    offset=0,
    radius_data=None,
):
    params = {
        "min_mag": min_mag,
        "max_mag": max_mag,
        "limit": limit,
        "offset": offset,
        "sort": sort,
    }
    if use_all_time:
        params["all_time"] = True
    else:
        params["days_back"] = days_back
    if radius_data:
        params.update(radius_data)
    return params


def change_events_page(delta):
    current_page = int(st.session_state.get("events_page", 1))
    st.session_state.events_page = max(1, current_page + delta)


def render_events_table(rows):
    if not rows:
        st.info("No hay eventos con los filtros actuales.")
        return

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df["Fecha UTC"] = df["time"].dt.strftime("%Y-%m-%d")
    df["Hora UTC"] = df["time"].dt.strftime("%H:%M")
    df["Mes UTC"] = df["time"].dt.strftime("%Y-%m")
    df["Ano UTC"] = df["time"].dt.strftime("%Y")
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
        "Fecha UTC",
        "Hora UTC",
        "Mes UTC",
        "Ano UTC",
        "Profundidad km",
        "Latitud",
        "Longitud",
        "Tipo",
        "Alerta",
        "Estado",
        "Distancia km",
    ]
    columns = [column for column in columns if column in df.columns]
    table_df = df[columns].copy()
    for column in ["Magnitud", "Profundidad km", "Latitud", "Longitud", "Distancia km"]:
        if column in table_df.columns:
            table_df[column] = pd.to_numeric(table_df[column], errors="coerce").round(2)

    table_html = table_df.to_html(
        index=False,
        escape=True,
        classes="events-table",
        border=0,
    )
    st.markdown(
        f"<div class='table-wrap'>{table_html}</div>",
        unsafe_allow_html=True,
    )


def region_from_place(place):
    if not place:
        return "Sin ubicacion"
    text = str(place).strip()
    if "," in text:
        return text.split(",")[-1].strip() or text
    if " of " in text:
        return text.split(" of ")[-1].strip() or text
    return text


def prepare_analysis_frame(rows):
    df = pd.DataFrame(rows).copy()
    df["mag"] = pd.to_numeric(df["mag"], errors="coerce")
    df["depth"] = pd.to_numeric(df["depth"], errors="coerce")
    df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
    df = df.dropna(subset=["mag"])
    bins = [-10, 2, 4, 6, 10]
    labels = ["Micro", "Leve", "Fuerte", "Severo"]
    df["Categoria"] = pd.cut(
        df["mag"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    ).astype(str)
    df["Region"] = df["place"].fillna("Sin ubicacion").apply(region_from_place)
    df["Dia"] = df["time"].dt.strftime("%Y-%m-%d")
    return df


def insight_text(counts, total):
    if total <= 0:
        return "Sin datos suficientes"
    severe = int(counts.get("Severo", 0))
    strong = int(counts.get("Fuerte", 0))
    if severe:
        return "Hay eventos severos en el analisis; conviene revisar detalle y ubicacion."
    if strong:
        return "Predominan eventos no severos, pero existen sismos fuertes relevantes."
    return "La actividad seleccionada se concentra en magnitudes micro o leves."


def chart_base(chart):
    return chart.properties(
        background="#fff8f0",
    ).configure_view(
        strokeWidth=0,
        fill="#fff8f0",
    ).configure_axis(
        labelColor="#24150f",
        titleColor="#6d5548",
        gridColor="#ead6c9",
        domainColor="#b9907d",
        tickColor="#b9907d",
        labelFont="Segoe UI",
        titleFont="Segoe UI",
        labelFontSize=12,
        titleFontSize=12,
    ).configure_legend(
        labelColor="#24150f",
        titleColor="#6d5548",
        labelFont="Segoe UI",
        titleFont="Segoe UI",
        labelFontSize=12,
        titleFontSize=12,
    ).configure_title(
        color="#4b2419",
        font="Segoe UI",
        fontSize=15,
        anchor="start",
    )


@st.cache_data(ttl=60, show_spinner=False)
def fetch_data(endpoint: str, params: tuple = ()) -> dict:
    query = dict(params)
    response = requests.get(
        f"{API_BASE_URL}/api/v1/{endpoint}",
        params=query,
        timeout=10,
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
        zoom_control=False,
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
        parsed_time = pd.to_datetime(eq.get("time"), errors="coerce", utc=True)
        if pd.isna(parsed_time):
            date_label = "--"
            hour_label = "--"
            month_label = "--"
            year_label = "--"
        else:
            date_label = parsed_time.strftime("%Y-%m-%d")
            hour_label = parsed_time.strftime("%H:%M UTC")
            month_label = parsed_time.strftime("%Y-%m")
            year_label = parsed_time.strftime("%Y")
        popup_html = (
            f"<b>{eq.get('place', 'Unknown')}</b><br>"
            f"Magnitud: {mag}<br>"
            f"Categoria: {magnitude_label(mag)}<br>"
            f"Profundidad: {eq.get('depth', 'N/A')} km<br>"
            f"Fecha UTC: {date_label}<br>"
            f"Hora UTC: {hour_label}<br>"
            f"Mes/Ano: {month_label} / {year_label}<br>"
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
        key="view_mode",
    )
    use_radius = view_mode == "Cerca de una zona"

    min_mag, max_mag = st.slider(
        "Magnitud que quieres ver",
        min_value=0.0,
        max_value=9.0,
        value=(0.0, 9.0),
        step=0.1,
        key="mag_range",
    )

    time_range = st.selectbox(
        "Periodo a consultar",
        ["Ultimas 24 horas", "7 dias", "30 dias", "1 Año", "10 años"],
        index=1,
        key="time_range",
    )
    days_back = {"Ultimas 24 horas": 1, "7 dias": 7, "30 dias": 30, "1 Año": 365, "10 años": 3650}[time_range]

    map_limit = st.slider(
        "Eventos visibles en mapa",
        50,
        1000,
        500,
        step=50,
        key="map_limit",
    )
    st.caption("Solo limita cuantos puntos se dibujan para que el mapa cargue rapido. La tabla puede recorrer todos por paginas.")

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
        key="map_style",
    )

    st.caption("Fuente: USGS Earthquake Catalog")

    with st.expander("Guia rapida"):
        st.write("1. Usa Eventos recientes para ver sismos globales.")
        st.write("2. Usa Cerca de una zona para buscar alrededor de un pais o escribir sus coordenadas.")
        st.write("3. Ajusta la magnitud para ocultar eventos muy pequenos.")
        st.write("4. Eventos visibles en mapa no borra datos; solo hace mas rapido el mapa.")
        st.write("5. En Eventos puedes usar Todos los eventos para recorrer la base por paginas.")
        st.write("6. El resumen tiene sus propios filtros dentro del tab Resumen.")

st.markdown(
    """
    <div class="hero">
        <h1>Monitor Sismico Global</h1>
        <p>Explora terremotos recientes, filtra por magnitud y busca actividad sismica cerca de una zona.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

health, health_error = safe_fetch("health", {"_": 1})
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

radius_params = {"lat": lat, "lon": lon, "dist_km": dist_km} if use_radius else None
map_params = build_event_params(
    min_mag=min_mag,
    max_mag=max_mag,
    days_back=days_back,
    use_all_time=False,
    limit=map_limit,
    offset=0,
    sort="distance" if use_radius else "recent",
    radius_data=radius_params,
)
if use_radius:
    data, data_error = safe_fetch("earthquakes/radius", map_params)
else:
    data, data_error = safe_fetch("earthquakes", map_params)

overview_params = {
    "min_mag": min_mag,
    "max_mag": max_mag,
    "days_back": days_back,
}
if use_radius:
    overview_params.update({"lat": lat, "lon": lon, "dist_km": dist_km})
overview_data, overview_error = safe_fetch("earthquakes/analysis", overview_params)

map_rows = [
    row for row in data.get("results", [])
    if float(row.get("mag") or 0) <= max_mag
]
filtered_total_from_list = int(data.get("total_count") or len(map_rows))

if data_error:
    st.warning(f"No se pudieron cargar eventos: {data_error}")
if overview_error:
    st.warning(f"No se pudieron cargar los indicadores principales: {overview_error}")

overview_summary = overview_data.get("summary") or {}
total_found = int(overview_summary.get("total_events") or filtered_total_from_list)
avg_depth = overview_summary.get("avg_depth")

metric_cols = st.columns(4)
metric_cols[0].metric("Eventos en base", format_number(stats.get("total_events")))
metric_cols[1].metric("Sismos encontrados", format_number(total_found))
metric_cols[2].metric("Eventos en mapa", format_number(len(map_rows)))
metric_cols[3].metric(
    "Magnitud mayor",
    format_number(overview_summary.get("max_magnitude")),
)
st.caption(
    f"Periodo: {time_range}. "
    f"El mapa dibuja hasta {map_limit:,} puntos."
)
st.caption(
    "Profundidad promedio: "
    + (f"{format_number(avg_depth)} km" if avg_depth is not None else "--"),
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
        fmap = build_map(map_rows, use_radius, lat, lon, dist_km, map_style)
        st_folium(fmap, width=None, height=570, key="main_map", use_container_width=True)
    with right:
        st.subheader("Vista actual")
        st.metric("Sismos encontrados", format_number(total_found))
        st.metric("Puntos en mapa", format_number(len(map_rows)))
        st.metric("Magnitud", f"{min_mag:.1f} - {max_mag:.1f}")
        st.caption(f"Periodo: {time_range}")
        if use_radius:
            st.metric("Distancia", f"{dist_km:,} km")
            st.caption(f"Centro: {lat:.2f}, {lon:.2f}")
        else:
            st.caption("Consulta global sin radio geografico.")

        if map_rows:
            strongest = max(map_rows, key=lambda item: float(item.get("mag") or 0))
            st.divider()
            st.subheader("Evento mayor")
            st.write(strongest.get("place", "Unknown"))
            st.metric("Magnitud", format_number(strongest.get("mag")))
            st.metric("Profundidad", f"{format_number(strongest.get('depth'))} km")
            st.caption(format_time(strongest.get("time")))

with tab_table:
    event_view = st.radio(
        "Vista de la tabla",
        list(EVENT_VIEW_OPTIONS.keys()),
        horizontal=True,
    )
    view_config = EVENT_VIEW_OPTIONS[event_view]
    st.caption(EVENT_VIEW_OPTIONS[event_view]["caption"])

    if view_config["paged"]:
        table_use_all_time = True
        page_size = TABLE_PAGE_SIZE
        table_signature = (
            use_radius,
            round(float(lat), 4),
            round(float(lon), 4),
            int(dist_km),
            round(float(min_mag), 1),
            round(float(max_mag), 1),
            event_view,
        )
        if st.session_state.get("events_table_signature") != table_signature:
            st.session_state.events_table_signature = table_signature
            st.session_state.events_page = 1

        endpoint = "earthquakes/radius" if use_radius else "earthquakes"
        page_number = max(int(st.session_state.get("events_page", 1)), 1)
        table_params = build_event_params(
            min_mag=min_mag,
            max_mag=max_mag,
            days_back=days_back,
            use_all_time=table_use_all_time,
            limit=page_size,
            offset=(page_number - 1) * page_size,
            sort=view_config["sort"],
            radius_data=radius_params,
        )
        table_data, table_error = safe_fetch(endpoint, table_params)
        table_rows = table_data.get("results", [])
        table_total = int(table_data.get("total_count") or 0)
        total_pages = max(1, ceil(max(table_total, 1) / page_size))
        if page_number > total_pages:
            st.session_state.events_page = total_pages
            page_number = total_pages
        st.session_state.events_page = page_number
        page_number = st.session_state.events_page

        prev_col, page_col, next_col = st.columns([1, 1.35, 1])
        if prev_col.button(
            "Pagina anterior",
            width="stretch",
            disabled=page_number <= 1,
            on_click=change_events_page,
            args=(-1,),
        ):
            pass
        page_col.markdown(
            f"<div class='table-note'><strong>Pagina {page_number:,} de {total_pages:,}</strong></div>",
            unsafe_allow_html=True,
        )
        if next_col.button(
            "Siguiente pagina",
            width="stretch",
            disabled=page_number >= total_pages,
            on_click=change_events_page,
            args=(1,),
        ):
            pass

        if table_error:
            st.warning(f"No se pudo cargar la pagina de eventos: {table_error}")
        render_events_table(table_rows)
    else:
        table_params = build_event_params(
            min_mag=min_mag,
            max_mag=max_mag,
            days_back=days_back,
            use_all_time=False,
            limit=map_limit,
            offset=0,
            sort=view_config["sort"],
            radius_data=radius_params,
        )
        endpoint = "earthquakes/radius" if use_radius else "earthquakes"
        table_data, table_error = safe_fetch(endpoint, table_params)
        table_rows = table_data.get("results", [])
        table_total = int(table_data.get("total_count") or total_found)
        if table_error:
            st.warning(f"No se pudieron cargar eventos de tabla: {table_error}")
        render_events_table(table_rows)

with tab_summary:
    analysis_data = overview_data
    analysis_summary = analysis_data.get("summary") or {}
    total_analyzed = int(analysis_summary.get("total_events") or 0)

    if total_analyzed > 0:
        labels = ["Micro", "Leve", "Fuerte", "Severo"]
        color_range = [
            MAG_COLORS["low"],
            MAG_COLORS["mid"],
            MAG_COLORS["high"],
            MAG_COLORS["severe"],
        ]
        counts = {
            label: int((analysis_data.get("category_counts") or {}).get(label, 0))
            for label in labels
        }
        counts_series = pd.Series(counts).reindex(labels, fill_value=0)
        dominant_category = counts_series.idxmax() if total_analyzed else "--"
        top_regions = analysis_data.get("top_regions") or []
        strongest_events = analysis_data.get("strongest_events") or []
        strongest = strongest_events[0] if strongest_events else {}
        active_region = top_regions[0].get("region", "--") if top_regions else "--"

        st.markdown(
            """
            <div class="analysis-title">
                <h2>Analisis de actividad sismica</h2>
                <p>Resumen agregado de todos los eventos que cumplen los filtros actuales.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        card_cols = st.columns(4)
        cards = [
            (
                "Lectura rapida",
                insight_text(counts, total_analyzed),
                f"{total_analyzed:,} eventos analizados",
            ),
            (
                "Categoria dominante",
                dominant_category,
                f"{int(counts.get(dominant_category, 0)):,} eventos en esta categoria",
            ),
            (
                "Evento mayor",
                f"M {format_number(strongest.get('mag'))}",
                escape(str(strongest.get("place", "Sin ubicacion"))),
            ),
            (
                "Zona mas repetida",
                escape(str(active_region)),
                "Aparece con mayor frecuencia en los eventos del resumen",
            ),
        ]
        for column, (label, value, note) in zip(card_cols, cards):
            column.markdown(
                f"""
                <div class="analysis-card">
                    <div class="label">{label}</div>
                    <div class="value">{value}</div>
                    <div class="note">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="section-band">
                <h3>Comportamiento general</h3>
                <p>Estas graficas resumen intensidad, zonas frecuentes y profundidad sin cargar todos los registros en pantalla.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        region_df = pd.DataFrame(top_regions).rename(
            columns={"region": "Region", "events": "Eventos", "avg_magnitude": "Magnitud prom."}
        )
        depth_df = pd.DataFrame(analysis_data.get("depth_groups") or []).rename(
            columns={"depth_group": "Profundidad", "events": "Eventos", "avg_magnitude": "Magnitud prom."}
        )

        left_chart, right_chart = st.columns([1.05, 1])
        with left_chart:
            dist_df = counts_series.reset_index()
            dist_df.columns = ["Categoria", "Eventos"]
            dist_chart = alt.Chart(dist_df).mark_bar(
                cornerRadiusEnd=5,
                size=26,
            ).encode(
                x=alt.X(
                    "Eventos:Q",
                    title="Eventos",
                    axis=alt.Axis(tickCount=5, format=",.0f"),
                ),
                y=alt.Y("Categoria:N", sort=labels, title=None),
                color=alt.Color(
                    "Categoria:N",
                    scale=alt.Scale(domain=labels, range=color_range),
                    legend=None,
                ),
                tooltip=["Categoria", "Eventos"],
            ).properties(
                height=240,
                title="Distribucion por magnitud",
            )
            st.altair_chart(chart_base(dist_chart), width="stretch", theme=None)

        with right_chart:
            if not region_df.empty:
                region_chart = alt.Chart(region_df).mark_bar(
                    cornerRadiusEnd=5,
                    color="#7a3f2a",
                ).encode(
                    x=alt.X(
                        "Eventos:Q",
                        title="Eventos",
                        axis=alt.Axis(tickCount=5, format=",.0f"),
                    ),
                    y=alt.Y("Region:N", sort="-x", title=None),
                    tooltip=["Region", "Eventos", "Magnitud prom."],
                ).properties(
                    height=240,
                    title="Zonas mas frecuentes",
                )
                st.altair_chart(chart_base(region_chart), width="stretch", theme=None)
            else:
                st.info("No hay zonas suficientes para graficar.")

        if not depth_df.empty:
            depth_chart = alt.Chart(depth_df).mark_bar(
                cornerRadiusEnd=5,
                color="#a85b36",
                size=34,
            ).encode(
                x=alt.X(
                    "Eventos:Q",
                    title="Eventos",
                    axis=alt.Axis(tickCount=5, format=",.0f"),
                ),
                y=alt.Y(
                    "Profundidad:N",
                    sort=["Superficial", "Intermedia", "Profunda"],
                    title=None,
                ),
                tooltip=["Profundidad", "Eventos", "Magnitud prom."],
            ).properties(
                height=210,
                title="Eventos por profundidad",
            )
            st.altair_chart(chart_base(depth_chart), width="stretch", theme=None)

        daily_df = pd.DataFrame(analysis_data.get("daily_counts") or []).rename(
            columns={"period": "Fecha", "events": "Eventos", "avg_magnitude": "Magnitud prom."}
        )
        monthly_df = pd.DataFrame(analysis_data.get("monthly_counts") or []).rename(
            columns={"period": "Mes", "events": "Eventos", "avg_magnitude": "Magnitud prom."}
        )
        yearly_df = pd.DataFrame(analysis_data.get("yearly_counts") or []).rename(
            columns={"period": "Ano", "events": "Eventos", "avg_magnitude": "Magnitud prom."}
        )
        st.markdown(
            """
            <div class="section-band">
                <h3>Actividad en el tiempo</h3>
                <p>Conteo de eventos por dia, mes y ano para entender cuando se concentra la actividad seleccionada.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not daily_df.empty:
            daily_df["Fecha"] = pd.to_datetime(daily_df["Fecha"], errors="coerce")
            daily_chart = alt.Chart(daily_df).mark_bar(
                color="#7a3f2a",
                cornerRadiusTopLeft=3,
                cornerRadiusTopRight=3,
            ).encode(
                x=alt.X("Fecha:T", title="Dia UTC", axis=alt.Axis(format="%d %b", labelAngle=-35)),
                y=alt.Y(
                    "Eventos:Q",
                    title="Cantidad de eventos",
                    axis=alt.Axis(tickCount=5, format=",.0f"),
                ),
                tooltip=[
                    alt.Tooltip("Fecha:T", title="Dia", format="%Y-%m-%d"),
                    "Eventos",
                    "Magnitud prom.",
                ],
            ).properties(
                height=260,
                title="Eventos por dia",
            )
            st.altair_chart(chart_base(daily_chart), width="stretch", theme=None)

        period_left, period_right = st.columns(2)
        with period_left:
            if not monthly_df.empty:
                monthly_chart = alt.Chart(monthly_df).mark_bar(
                    color="#a85b36",
                    cornerRadiusEnd=5,
                ).encode(
                    x=alt.X("Mes:N", title="Mes UTC", sort=None),
                    y=alt.Y(
                        "Eventos:Q",
                        title="Cantidad",
                        axis=alt.Axis(tickCount=5, format=",.0f"),
                    ),
                    tooltip=["Mes", "Eventos", "Magnitud prom."],
                ).properties(
                    height=210,
                    title="Eventos por mes",
                )
                st.altair_chart(chart_base(monthly_chart), width="stretch", theme=None)
        with period_right:
            if not yearly_df.empty:
                yearly_chart = alt.Chart(yearly_df).mark_bar(
                    color="#2f855a",
                    cornerRadiusEnd=5,
                ).encode(
                    x=alt.X("Ano:N", title="Ano UTC", sort=None),
                    y=alt.Y(
                        "Eventos:Q",
                        title="Cantidad",
                        axis=alt.Axis(tickCount=5, format=",.0f"),
                    ),
                    tooltip=["Ano", "Eventos", "Magnitud prom."],
                ).properties(
                    height=210,
                    title="Eventos por ano",
                )
                st.altair_chart(chart_base(yearly_chart), width="stretch", theme=None)

        st.markdown(
            """
            <div class="section-band">
                <h3>Eventos destacados</h3>
                <p>Los sismos con mayor magnitud dentro de los eventos del resumen.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for event in strongest_events:
            place = escape(str(event.get("place", "Sin ubicacion")))
            category = escape(magnitude_label(event.get("mag")))
            event_time = format_time(event.get("time"))
            depth = format_number(event.get("depth"))
            st.markdown(
                f"""
                <div class="event-row">
                    <div>
                        <div class="place">{place}</div>
                        <div class="meta">{category} - {event_time} - {depth} km profundidad</div>
                    </div>
                    <div class="mag">M {format_number(event.get("mag"))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Ajusta los filtros para ver resumen.")
