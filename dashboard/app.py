import os
import unicodedata
from html import escape
from math import ceil, isfinite, pi, sqrt

import altair as alt
import folium
import pandas as pd
import requests
import streamlit as st
from branca.element import MacroElement
from jinja2 import Template
from streamlit_folium import st_folium

try:
    from countryinfo import CountryInfo
except ImportError:
    CountryInfo = None

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001").rstrip("/")

EXTRA_LOCATION_PRESETS = {
    "Personalizado": {"lat": 8.9824, "lon": -79.5199, "radius": 600},
    "Afganistán": {"lat": 33.9391, "lon": 67.7100, "radius": 900},
    "Alaska": {"lat": 64.2008, "lon": -149.4937, "radius": 1000},
    "Alemania": {"lat": 51.1657, "lon": 10.4515, "radius": 650},
    "Argentina": {"lat": -38.4161, "lon": -63.6167, "radius": 1400},
    "Australia": {"lat": -25.2744, "lon": 133.7751, "radius": 1800},
    "Bolivia": {"lat": -16.2902, "lon": -63.5887, "radius": 900},
    "Brasil": {"lat": -14.2350, "lon": -51.9253, "radius": 1800},
    "California": {"lat": 36.7783, "lon": -119.4179, "radius": 700},
    "Canadá": {"lat": 56.1304, "lon": -106.3468, "radius": 1800},
    "Chile": {"lat": -33.4489, "lon": -70.6693, "radius": 900},
    "China": {"lat": 35.8617, "lon": 104.1954, "radius": 1800},
    "Colombia": {"lat": 4.5709, "lon": -74.2973, "radius": 850},
    "Costa Rica": {"lat": 9.7489, "lon": -83.7534, "radius": 500},
    "Ecuador": {"lat": -1.8312, "lon": -78.1834, "radius": 650},
    "El Salvador": {"lat": 13.7942, "lon": -88.8965, "radius": 450},
    "España": {"lat": 40.4637, "lon": -3.7492, "radius": 750},
    "Estados Unidos": {"lat": 39.8283, "lon": -98.5795, "radius": 2000},
    "Filipinas": {"lat": 12.8797, "lon": 121.7740, "radius": 900},
    "Francia": {"lat": 46.2276, "lon": 2.2137, "radius": 750},
    "Grecia": {"lat": 39.0742, "lon": 21.8243, "radius": 650},
    "Guatemala": {"lat": 15.7835, "lon": -90.2308, "radius": 550},
    "Haití": {"lat": 18.9712, "lon": -72.2852, "radius": 450},
    "Honduras": {"lat": 15.2000, "lon": -86.2419, "radius": 550},
    "India": {"lat": 20.5937, "lon": 78.9629, "radius": 1700},
    "Indonesia": {"lat": -0.7893, "lon": 113.9213, "radius": 1700},
    "Irán": {"lat": 32.4279, "lon": 53.6880, "radius": 1100},
    "Italia": {"lat": 41.8719, "lon": 12.5674, "radius": 650},
    "Jamaica": {"lat": 18.1096, "lon": -77.2975, "radius": 350},
    "Japón": {"lat": 38.5000, "lon": 142.0000, "radius": 900},
    "México": {"lat": 19.4326, "lon": -99.1332, "radius": 900},
    "Nepal": {"lat": 28.3949, "lon": 84.1240, "radius": 650},
    "Nicaragua": {"lat": 12.8654, "lon": -85.2072, "radius": 500},
    "Nueva Zelanda": {"lat": -40.9006, "lon": 174.8860, "radius": 850},
    "Pakistan": {"lat": 30.3753, "lon": 69.3451, "radius": 1000},
    "Panamá": {"lat": 8.9824, "lon": -79.5199, "radius": 600},
    "Papua Nueva Guinea": {"lat": -6.3150, "lon": 143.9555, "radius": 900},
    "Perú": {"lat": -9.1900, "lon": -75.0152, "radius": 950},
    "Puerto Rico": {"lat": 18.2208, "lon": -66.5901, "radius": 350},
    "República Dominicana": {"lat": 18.7357, "lon": -70.1627, "radius": 350},
    "Rusia": {"lat": 61.5240, "lon": 105.3188, "radius": 2200},
    "Taiwán": {"lat": 23.6978, "lon": 120.9605, "radius": 450},
    "Turquía": {"lat": 38.9637, "lon": 35.2433, "radius": 900},
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
    "Más recientes": {
        "sort": "recent",
        "paged": False,
        "caption": "Ordena por fecha UTC, del evento más nuevo al más antiguo.",
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
        "caption": "Recorre todo lo cargado en la base por páginas; respeta magnitud y zona seleccionada.",
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


def normalize_location_name(name):
    """Crea una clave comparable ignorando tildes, mayúsculas y espacios repetidos."""
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(text.casefold().split())


def coordinates_from_map_click(last_clicked):
    """Valida y extrae coordenadas entregadas por Leaflet al hacer clic."""
    if not isinstance(last_clicked, dict):
        return None
    try:
        latitude = float(last_clicked["lat"])
        longitude = float(last_clicked["lng"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (isfinite(latitude) and isfinite(longitude) and -90 <= latitude <= 90):
        return None
    # Leaflet puede devolver longitudes de mundos envueltos (p. ej. 280°).
    # Se convierten siempre al mundo canónico [-180, 180].
    longitude = ((longitude + 180) % 360) - 180
    return latitude, longitude


def build_location_presets():
    presets = dict(EXTRA_LOCATION_PRESETS)
    canonical_names = {
        normalize_location_name(name)
        for name in presets
    }
    country_codes = set()
    if CountryInfo is not None:
        try:
            for source_name, info in CountryInfo.all().items():
                latlng = info.get("latlng") or []
                translations = info.get("translations") or {}
                display_name = (
                    translations.get("es")
                    or info.get("nativeName")
                    or info.get("name")
                    or source_name
                )
                display_name = " ".join(str(display_name).split())
                if display_name:
                    display_name = display_name[0].upper() + display_name[1:]

                iso = info.get("ISO") or {}
                country_code = iso.get("alpha3") or iso.get("alpha2")
                canonical_name = normalize_location_name(display_name)
                repeated_code = country_code and country_code in country_codes

                if (
                    len(latlng) >= 2
                    and canonical_name
                    and canonical_name not in canonical_names
                    and not repeated_code
                ):
                    presets[display_name] = {
                        "lat": float(latlng[0]),
                        "lon": float(latlng[1]),
                        "radius": estimate_country_radius(info.get("area")),
                    }
                    canonical_names.add(canonical_name)
                if country_code:
                    country_codes.add(country_code)
        except Exception:
            pass

    first = {"Personalizado": presets["Personalizado"]}
    rest = {
        name: presets[name]
        for name in sorted(presets, key=normalize_location_name)
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


class KeepWheelEventsInsideMap(MacroElement):
    """Evita que la rueda sobre Leaflet desplace la página de Streamlit."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        const mapContainer = {{ this._parent.get_name() }}.getContainer();
        L.DomEvent.disableScrollPropagation(mapContainer);
        mapContainer.addEventListener('wheel', function(event) {
            event.preventDefault();
            event.stopPropagation();
        }, { passive: false });
        {% endmacro %}
        """
    )


class NonInteractiveSearchAreaPane(MacroElement):
    """Capa visual para el radio y centro que nunca intercepta el mouse."""

    _template = Template(
        """
        {% macro script(this, kwargs) %}
        const searchAreaPane = {{ this._parent.get_name() }}.createPane('searchAreaPane');
        searchAreaPane.style.zIndex = 350;
        searchAreaPane.style.pointerEvents = 'none';
        {% endmacro %}
        """
    )

st.set_page_config(
    page_title="Monitor Sísmico",
    layout="wide",
    initial_sidebar_state="auto",
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
    }
    header[data-testid="stHeader"] svg {
        color: var(--ink) !important;
    }
    header[data-testid="stHeader"] svg path[fill="none"] {
        fill: none !important;
        stroke: none !important;
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
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepDown"],
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepUp"] {
        background: #f0d9c7 !important;
        color: #24150f !important;
        border-color: #b98b72 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepDown"]:hover,
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepUp"]:hover {
        background: #dfbfa8 !important;
        color: #24150f !important;
        border-color: #7a3f2a !important;
    }
    section[data-testid="stSidebar"] [data-testid="stNumberInputIcon"],
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepDown"] svg,
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepUp"] svg,
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepDown"] svg *,
    section[data-testid="stSidebar"] [data-testid="stNumberInputStepUp"] svg * {
        color: #24150f !important;
        fill: #24150f !important;
        stroke: #24150f !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] input[type="number"] {
        color-scheme: light !important;
    }
    section[data-testid="stSidebar"] input[type="number"]::-webkit-inner-spin-button,
    section[data-testid="stSidebar"] input[type="number"]::-webkit-outer-spin-button {
        filter: brightness(0.25) !important;
        opacity: 1 !important;
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
        return fallback
    if not isfinite(number):
        return fallback
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def finite_numeric(series, fill_value=None):
    """Convierte una serie a números y descarta NaN e infinitos."""
    numeric = pd.to_numeric(series, errors="coerce")
    numeric = numeric.where(
        numeric.map(lambda value: pd.isna(value) or isfinite(float(value)))
    )
    return numeric.fillna(fill_value) if fill_value is not None else numeric


def format_time(value):
    if value is None or value == "":
        return "--"
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return "--"
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def format_period_label(use_all_time, days_back):
    return "Todo lo cargado" if use_all_time else f"Últimos {days_back} días"


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
    df["Año UTC"] = df["time"].dt.strftime("%Y")
    df["Categoría"] = df["mag"].apply(magnitude_label)
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
        "Categoría",
        "Lugar",
        "Fecha UTC",
        "Hora UTC",
        "Mes UTC",
        "Año UTC",
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
        na_rep="--",
    )
    st.markdown(
        f"<div class='table-wrap'>{table_html}</div>",
        unsafe_allow_html=True,
    )


def region_from_place(place):
    if not place:
        return "Sin ubicación"
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
    df["Categoría"] = pd.cut(
        df["mag"],
        bins=bins,
        labels=labels,
        include_lowest=True,
    ).astype(str)
    df["Región"] = df["place"].fillna("Sin ubicación").apply(region_from_place)
    df["Día"] = df["time"].dt.strftime("%Y-%m-%d")
    return df


def insight_text(counts, total):
    if total <= 0:
        return "Sin datos suficientes"
    severe = int(counts.get("Severo", 0))
    strong = int(counts.get("Fuerte", 0))
    if severe:
        return "Hay eventos severos en el análisis; conviene revisar detalle y ubicación."
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


@st.cache_data(ttl=120, show_spinner=False)
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


def build_map(
    rows,
    use_radius,
    lat,
    lon,
    dist_km,
    map_style,
    allow_map_recenter=False,
    selected_event_id=None,
):
    if use_radius:
        location = [lat, lon]
        if dist_km <= 25:
            zoom_start = 8
        elif dist_km <= 100:
            zoom_start = 6
        elif dist_km <= 300:
            zoom_start = 5
        elif dist_km <= 800:
            zoom_start = 4
        else:
            zoom_start = 3
    elif rows:
        avg_lat = sum(float(r["latitude"]) for r in rows) / len(rows)
        avg_lon = sum(float(r["longitude"]) for r in rows) / len(rows)
        location = [avg_lat, avg_lon]
        zoom_start = 3
    else:
        location = [lat, lon]
        zoom_start = 4

    fmap = folium.Map(
        location=location,
        zoom_start=zoom_start,
        min_zoom=3,
        max_zoom=19,
        world_copy_jump=True,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
        scroll_wheel_zoom=True,
        zoom_control=False,
    )
    KeepWheelEventsInsideMap().add_to(fmap)
    style = MAP_STYLES.get(map_style, MAP_STYLES["Claro detallado"])
    folium.TileLayer(
        tiles=style["tiles"],
        attr=style["attr"],
        name=map_style,
        detect_retina=True,
        min_zoom=3,
        max_zoom=19,
    ).add_to(fmap)

    if use_radius:
        # La zona de búsqueda se dibuja primero y no recibe eventos del mouse;
        # así nunca tapa el hover o el clic de los sismos colocados encima.
        NonInteractiveSearchAreaPane().add_to(fmap)
        folium.Circle(
            location=[lat, lon],
            radius=dist_km * 1000,
            color="#2563eb",
            fill=True,
            fill_opacity=0.05,
            weight=2,
            interactive=False,
            bubbling_mouse_events=allow_map_recenter,
            pane="searchAreaPane",
        ).add_to(fmap)
        folium.Marker(
            location=[lat, lon],
            icon=folium.Icon(color="blue", icon="crosshairs", prefix="fa"),
            interactive=False,
            pane="searchAreaPane",
        ).add_to(fmap)

    for eq in rows:
        mag = float(eq.get("mag") or 0)
        color = magnitude_color(mag)
        radius = max(4, min(6 + mag * 2.2, 24))
        usgs_id = str(eq.get("usgs_id") or "")
        place_label = escape(str(eq.get("place") or "Sin ubicación"))
        depth_label = format_number(eq.get("depth"))
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
        distance_html = ""
        if eq.get("distance_km") is not None:
            distance_html = f"Distancia: {format_number(eq.get('distance_km'))} km<br>"

        tooltip_html = (
            "<div style='min-width:190px'>"
            f"<strong>{place_label}</strong><br>"
            f"Magnitud: <strong>M {mag:.1f}</strong><br>"
            f"Profundidad: {depth_label} km<br>"
            f"Fecha: {date_label} · {hour_label}"
            "</div>"
        )
        popup_html = (
            f"<b>{place_label}</b><br>"
            f"ID USGS: {escape(usgs_id)}<br>"
            f"Magnitud: {mag:.1f}<br>"
            f"Categoría: {magnitude_label(mag)}<br>"
            f"Profundidad: {depth_label} km<br>"
            f"{distance_html}"
            f"Fecha UTC: {date_label}<br>"
            f"Hora UTC: {hour_label}<br>"
            f"Mes/Año: {month_label} / {year_label}"
        )

        folium.CircleMarker(
            location=[eq["latitude"], eq["longitude"]],
            radius=radius,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.72,
            bubbling_mouse_events=False,
            tooltip=folium.Tooltip(
                tooltip_html,
                sticky=True,
                direction="top",
                opacity=0.96,
            ),
            popup=folium.Popup(
                popup_html,
                max_width=320,
                show=usgs_id == selected_event_id,
            ),
        ).add_to(fmap)

    return fmap


def store_custom_coordinates_from_inputs(lat_input_key, lon_input_key):
    """Copia valores de widgets condicionales a claves que Streamlit no elimina."""
    if lat_input_key in st.session_state:
        st.session_state.custom_lat = float(st.session_state[lat_input_key])
    if lon_input_key in st.session_state:
        st.session_state.custom_lon = float(st.session_state[lon_input_key])
    st.session_state.custom_coordinate_source = "manual"


@st.fragment
def render_events_tab(
    use_radius,
    lat,
    lon,
    dist_km,
    min_mag,
    max_mag,
    days_back,
    map_limit,
    radius_params,
):
    """Renderiza y actualiza la tabla sin reconstruir el mapa completo."""
    event_view = st.radio(
        "Vista de la tabla",
        list(EVENT_VIEW_OPTIONS.keys()),
        horizontal=True,
        key="event_view",
    )
    view_config = EVENT_VIEW_OPTIONS[event_view]
    st.caption(view_config["caption"])

    endpoint = "earthquakes/radius" if use_radius else "earthquakes"
    if view_config["paged"]:
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

        page_number = max(int(st.session_state.get("events_page", 1)), 1)
        table_params = build_event_params(
            min_mag=min_mag,
            max_mag=max_mag,
            days_back=days_back,
            use_all_time=True,
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
            page_number = total_pages
            st.session_state.events_page = total_pages
            table_params["offset"] = (page_number - 1) * page_size
            table_data, table_error = safe_fetch(endpoint, table_params)
            table_rows = table_data.get("results", [])

        prev_col, page_col, next_col = st.columns([1, 1.35, 1])
        prev_col.button(
            "Página anterior",
            width="stretch",
            disabled=page_number <= 1,
            on_click=change_events_page,
            args=(-1,),
        )
        page_col.markdown(
            f"<div class='table-note'><strong>Página {page_number:,} de {total_pages:,}</strong></div>",
            unsafe_allow_html=True,
        )
        next_col.button(
            "Siguiente página",
            width="stretch",
            disabled=page_number >= total_pages,
            on_click=change_events_page,
            args=(1,),
        )

        if table_error:
            st.warning(f"No se pudo cargar la página de eventos: {table_error}")
        render_events_table(table_rows)
        return

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
    table_data, table_error = safe_fetch(endpoint, table_params)
    table_rows = table_data.get("results", [])
    if table_error:
        st.warning(f"No se pudieron cargar eventos de tabla: {table_error}")
    render_events_table(table_rows)


pending_custom_coordinates = st.session_state.pop("pending_custom_coordinates", None)
if pending_custom_coordinates is not None:
    st.session_state.custom_lat = pending_custom_coordinates[0]
    st.session_state.custom_lon = pending_custom_coordinates[1]
    # Una identidad nueva evita que el navegador restaure el valor anterior.
    st.session_state.custom_coordinates_revision = (
        int(st.session_state.get("custom_coordinates_revision", 0)) + 1
    )

if "custom_lat" not in st.session_state:
    st.session_state.custom_lat = EXTRA_LOCATION_PRESETS["Personalizado"]["lat"]
if "custom_lon" not in st.session_state:
    st.session_state.custom_lon = EXTRA_LOCATION_PRESETS["Personalizado"]["lon"]
if "custom_coordinates_revision" not in st.session_state:
    st.session_state.custom_coordinates_revision = 0

custom_lat_input_key = f"custom_lat_input_{st.session_state.custom_coordinates_revision}"
custom_lon_input_key = f"custom_lon_input_{st.session_state.custom_coordinates_revision}"

preset = None
with st.sidebar:
    st.header("Panel de control")

    view_mode = st.radio(
        "¿Qué quieres explorar?",
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
        "Período a consultar",
        ["Últimas 24 horas", "7 días", "30 días", "1 año", "10 años"],
        index=1,
        key="time_range",
    )
    days_back = {"Últimas 24 horas": 1, "7 días": 7, "30 días": 30, "1 año": 365, "10 años": 3650}[time_range]

    map_limit = st.slider(
        "Eventos visibles en mapa",
        50,
        1000,
        500,
        step=50,
        key="map_limit",
    )
    st.caption("Solo limita cuántos puntos se dibujan para que el mapa cargue rápido. La tabla puede recorrer todos por páginas.")

    lat = LOCATION_PRESETS["Panamá"]["lat"]
    lon = LOCATION_PRESETS["Panamá"]["lon"]
    dist_km = LOCATION_PRESETS["Panamá"]["radius"]

    st.divider()
    if use_radius:
        st.subheader("Buscar cerca de")
        preset = st.selectbox(
            "País o zona",
            list(LOCATION_PRESETS.keys()),
            help="Puedes escribir dentro del selector para encontrar rápido un país.",
        )
        preset_data = LOCATION_PRESETS[preset]

        if preset == "Personalizado":
            lat = st.number_input(
                "Latitud",
                min_value=-90.0,
                max_value=90.0,
                value=float(st.session_state.custom_lat),
                step=0.0001,
                format="%.4f",
                key=custom_lat_input_key,
                on_change=store_custom_coordinates_from_inputs,
                args=(custom_lat_input_key, custom_lon_input_key),
            )
            lon = st.number_input(
                "Longitud",
                min_value=-180.0,
                max_value=180.0,
                value=float(st.session_state.custom_lon),
                step=0.0001,
                format="%.4f",
                key=custom_lon_input_key,
                on_change=store_custom_coordinates_from_inputs,
                args=(custom_lat_input_key, custom_lon_input_key),
            )
            dist_km = st.slider("Distancia alrededor", 10, 2000, preset_data["radius"], step=10)
            if st.session_state.get("custom_coordinate_source") == "map":
                st.caption("Coordenadas seleccionadas directamente en el mapa.")
        else:
            lat = preset_data["lat"]
            lon = preset_data["lon"]
            dist_km = st.slider("Distancia alrededor", 10, 2000, preset_data["radius"], step=10)
        st.caption("Escribe en el selector para buscar un país. Si no aparece, usa Personalizado y coloca coordenadas.")
    else:
        st.caption("Eventos recientes muestra sismos globales. Usa Cerca de una zona para buscar por ubicación.")

    st.divider()
    map_style = st.selectbox(
        "Tipo de mapa",
        list(MAP_STYLES.keys()),
        key="map_style",
    )

    st.caption("Fuente: USGS Earthquake Catalog")

    with st.expander("Guia rapida"):
        st.write("1. Usa Eventos recientes para ver sismos globales.")
        st.write("2. Usa Cerca de una zona para buscar alrededor de un país o escribir sus coordenadas.")
        st.write("3. Ajusta la magnitud para ocultar eventos muy pequeños.")
        st.write("4. Eventos visibles en mapa no borra datos; solo hace más rápido el mapa.")
        st.write("5. En Eventos puedes usar Todos los eventos para recorrer la base por páginas.")
        st.write("6. Mapa, Eventos y Resumen respetan los filtros del panel lateral.")

st.markdown(
    """
    <div class="hero">
        <h1>Monitor Sísmico Global</h1>
        <p>Explora terremotos recientes, filtra por magnitud y busca actividad sísmica cerca de una zona.</p>
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
        <span><strong>Última actualización:</strong> {format_time(stats.get("last_update"))}</span>
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
    f"Período: {time_range}. "
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
        custom_map_selection = use_radius and preset == "Personalizado"
        if custom_map_selection:
            st.info(
                "Haz clic en una zona vacía del mapa para usar ese punto como "
                "centro de la búsqueda."
            )
        fmap = build_map(
            map_rows,
            use_radius,
            lat,
            lon,
            dist_km,
            map_style,
            allow_map_recenter=custom_map_selection,
            selected_event_id=st.session_state.get("selected_map_event_id"),
        )
        map_state = st_folium(
            fmap,
            width=None,
            height=570,
            key="main_map_custom" if custom_map_selection else "main_map",
            returned_objects=["last_clicked", "last_object_clicked"]
            if custom_map_selection
            else [],
        )
        if custom_map_selection:
            clicked_coordinates = coordinates_from_map_click(
                (map_state or {}).get("last_clicked")
            )
            if clicked_coordinates is not None:
                object_coordinates = coordinates_from_map_click(
                    (map_state or {}).get("last_object_clicked")
                )
                selected_event_id = None
                if object_coordinates is not None:
                    for row in map_rows:
                        row_lat = float(row.get("latitude"))
                        row_lon = float(row.get("longitude"))
                        if (
                            abs(row_lat - object_coordinates[0]) < 0.000001
                            and abs(row_lon - object_coordinates[1]) < 0.000001
                        ):
                            selected_event_id = str(row.get("usgs_id") or "")
                            break
                st.session_state.selected_map_event_id = selected_event_id
                click_signature = tuple(round(value, 7) for value in clicked_coordinates)
                if st.session_state.get("last_custom_map_click") != click_signature:
                    st.session_state.last_custom_map_click = click_signature
                    st.session_state.pending_custom_coordinates = clicked_coordinates
                    st.session_state.custom_coordinate_source = "map"
                    st.rerun()
    with right:
        st.subheader("Vista actual")
        st.metric("Sismos encontrados", format_number(total_found))
        st.metric("Puntos en mapa", format_number(len(map_rows)))
        st.metric("Magnitud", f"{min_mag:.1f} - {max_mag:.1f}")
        st.caption(f"Período: {time_range}")
        if use_radius:
            st.metric("Distancia", f"{dist_km:,} km")
            st.caption(f"Centro: {lat:.2f}, {lon:.2f}")
        else:
            st.caption("Consulta global sin radio geográfico.")

        if map_rows:
            strongest = max(map_rows, key=lambda item: float(item.get("mag") or 0))
            st.divider()
            st.subheader("Evento mayor")
            st.write(strongest.get("place", "Unknown"))
            st.metric("Magnitud", format_number(strongest.get("mag")))
            st.metric("Profundidad", f"{format_number(strongest.get('depth'))} km")
            st.caption(format_time(strongest.get("time")))

with tab_table:
    render_events_tab(
        use_radius=use_radius,
        lat=lat,
        lon=lon,
        dist_km=dist_km,
        min_mag=min_mag,
        max_mag=max_mag,
        days_back=days_back,
        map_limit=map_limit,
        radius_params=radius_params,
    )

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
                <h2>Análisis de actividad sísmica</h2>
                <p>Resumen agregado de todos los eventos que cumplen los filtros actuales.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        card_cols = st.columns(5)
        cards = [
            (
                "Lectura rapida",
                insight_text(counts, total_analyzed),
                f"{total_analyzed:,} eventos analizados",
            ),
            (
                "Categoría dominante",
                dominant_category,
                f"{int(counts.get(dominant_category, 0)):,} eventos en esta categoría",
            ),
            (
                "Magnitud promedio",
                f"M {format_number(analysis_summary.get('avg_magnitude'))}",
                "Promedio de los eventos que cumplen los filtros",
            ),
            (
                "Evento mayor",
                f"M {format_number(strongest.get('mag'))}",
                escape(str(strongest.get("place", "Sin ubicación"))),
            ),
            (
                "Zona más repetida",
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
                <p>Estas gráficas resumen intensidad, zonas frecuentes y profundidad sin cargar todos los registros en pantalla.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        region_df = pd.DataFrame(top_regions).rename(
            columns={"region": "Región", "events": "Eventos", "avg_magnitude": "Magnitud promedio"}
        )
        depth_df = pd.DataFrame(analysis_data.get("depth_groups") or []).rename(
            columns={"depth_group": "Profundidad", "events": "Eventos", "avg_magnitude": "Magnitud promedio"}
        )
        for analysis_df in (region_df, depth_df):
            if not analysis_df.empty:
                analysis_df["Eventos"] = finite_numeric(
                    analysis_df["Eventos"], fill_value=0
                )
                analysis_df["Magnitud promedio"] = finite_numeric(
                    analysis_df["Magnitud promedio"]
                )

        left_chart, right_chart = st.columns([1.05, 1])
        with left_chart:
            dist_df = counts_series.reset_index()
            dist_df.columns = ["Categoría", "Eventos"]
            dist_chart = alt.Chart(dist_df).mark_bar(
                cornerRadiusEnd=5,
                size=26,
            ).encode(
                x=alt.X(
                    "Eventos:Q",
                    title="Eventos",
                    axis=alt.Axis(tickCount=5, format=",.0f"),
                ),
                y=alt.Y("Categoría:N", sort=labels, title=None),
                color=alt.Color(
                    "Categoría:N",
                    scale=alt.Scale(domain=labels, range=color_range),
                    legend=None,
                ),
                tooltip=["Categoría", "Eventos"],
            ).properties(
                height=240,
                title="Distribución por magnitud",
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
                    y=alt.Y("Región:N", sort="-x", title=None),
                    tooltip=[
                        alt.Tooltip("Región:N"),
                        alt.Tooltip("Eventos:Q", format=",.0f"),
                        alt.Tooltip(
                            "Magnitud promedio:Q",
                            title="Magnitud promedio",
                            format=".2f",
                        ),
                    ],
                ).properties(
                    height=240,
                    title="Zonas más frecuentes",
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
                tooltip=[
                    alt.Tooltip("Profundidad:N"),
                    alt.Tooltip("Eventos:Q", format=",.0f"),
                    alt.Tooltip(
                        "Magnitud promedio:Q",
                        title="Magnitud promedio",
                        format=".2f",
                    ),
                ],
            ).properties(
                height=210,
                title="Eventos por profundidad",
            )
            st.altair_chart(chart_base(depth_chart), width="stretch", theme=None)

        daily_df = pd.DataFrame(analysis_data.get("daily_counts") or []).rename(
            columns={"period": "Fecha", "events": "Eventos", "avg_magnitude": "Magnitud promedio"}
        )
        monthly_df = pd.DataFrame(analysis_data.get("monthly_counts") or []).rename(
            columns={"period": "Mes", "events": "Eventos", "avg_magnitude": "Magnitud promedio"}
        )
        yearly_df = pd.DataFrame(analysis_data.get("yearly_counts") or []).rename(
            columns={"period": "Año", "events": "Eventos", "avg_magnitude": "Magnitud promedio"}
        )
        for period_df in (daily_df, monthly_df, yearly_df):
            if not period_df.empty:
                period_df["Eventos"] = finite_numeric(
                    period_df["Eventos"], fill_value=0
                )
                period_df["Magnitud promedio"] = finite_numeric(
                    period_df["Magnitud promedio"]
                )
        st.markdown(
            """
            <div class="section-band">
                <h3>Actividad en el tiempo</h3>
                <p>Conteo de eventos por día, mes y año para entender cuándo se concentra la actividad seleccionada.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not daily_df.empty:
            daily_df["Fecha"] = pd.to_datetime(daily_df["Fecha"], errors="coerce")
            daily_df = daily_df.dropna(subset=["Fecha"])
            daily_base = alt.Chart(daily_df)
            daily_bars = daily_base.mark_bar(
                color="#7a3f2a",
                cornerRadiusTopLeft=3,
                cornerRadiusTopRight=3,
            ).encode(
                x=alt.X("Fecha:T", title="Día UTC", axis=alt.Axis(format="%d %b", labelAngle=-35)),
                y=alt.Y(
                    "Eventos:Q",
                    title="Cantidad de eventos",
                    axis=alt.Axis(tickCount=5, format=",.0f"),
                ),
                tooltip=[
                    alt.Tooltip("Fecha:T", title="Día", format="%Y-%m-%d"),
                    alt.Tooltip("Eventos:Q", format=",.0f"),
                    alt.Tooltip(
                        "Magnitud promedio:Q",
                        title="Magnitud promedio",
                        format=".2f",
                    ),
                ],
            )
            daily_average = daily_base.mark_line(
                color="#2563eb",
                point=alt.OverlayMarkDef(color="#2563eb", filled=True, size=45),
                strokeWidth=2.5,
            ).encode(
                x=alt.X("Fecha:T"),
                y=alt.Y(
                    "Magnitud promedio:Q",
                    title="Magnitud promedio",
                    axis=alt.Axis(titleColor="#2563eb", format=".1f"),
                    scale=alt.Scale(zero=False),
                ),
                tooltip=[
                    alt.Tooltip("Fecha:T", title="Día", format="%Y-%m-%d"),
                    alt.Tooltip(
                        "Magnitud promedio:Q",
                        title="Magnitud promedio",
                        format=".2f",
                    ),
                ],
            )
            daily_chart = alt.layer(daily_bars, daily_average).resolve_scale(
                y="independent"
            ).properties(
                height=260,
                title="Eventos y magnitud promedio por día",
            )
            st.altair_chart(chart_base(daily_chart), width="stretch", theme=None)

        period_left, period_right = st.columns(2)
        with period_left:
            if not monthly_df.empty:
                monthly_base = alt.Chart(monthly_df)
                monthly_bars = monthly_base.mark_bar(
                    color="#a85b36",
                    cornerRadiusEnd=5,
                ).encode(
                    x=alt.X("Mes:N", title="Mes UTC", sort=None),
                    y=alt.Y(
                        "Eventos:Q",
                        title="Cantidad",
                        axis=alt.Axis(tickCount=5, format=",.0f"),
                    ),
                    tooltip=[
                        alt.Tooltip("Mes:N"),
                        alt.Tooltip("Eventos:Q", format=",.0f"),
                        alt.Tooltip(
                            "Magnitud promedio:Q",
                            title="Magnitud promedio",
                            format=".2f",
                        ),
                    ],
                )
                monthly_average = monthly_base.mark_line(
                    color="#2563eb",
                    point=alt.OverlayMarkDef(color="#2563eb", filled=True, size=50),
                    strokeWidth=2.5,
                ).encode(
                    x=alt.X("Mes:N", sort=None),
                    y=alt.Y(
                        "Magnitud promedio:Q",
                        title="Magnitud promedio",
                        axis=alt.Axis(titleColor="#2563eb", format=".1f"),
                        scale=alt.Scale(zero=False),
                    ),
                    tooltip=[
                        alt.Tooltip("Mes:N"),
                        alt.Tooltip(
                            "Magnitud promedio:Q",
                            title="Magnitud promedio",
                            format=".2f",
                        ),
                    ],
                )
                monthly_chart = alt.layer(
                    monthly_bars, monthly_average
                ).resolve_scale(y="independent").properties(
                    height=210,
                    title="Eventos y magnitud promedio por mes",
                )
                st.altair_chart(chart_base(monthly_chart), width="stretch", theme=None)
        with period_right:
            if not yearly_df.empty:
                yearly_base = alt.Chart(yearly_df)
                yearly_bars = yearly_base.mark_bar(
                    color="#2f855a",
                    cornerRadiusEnd=5,
                ).encode(
                    x=alt.X("Año:N", title="Año UTC", sort=None),
                    y=alt.Y(
                        "Eventos:Q",
                        title="Cantidad",
                        axis=alt.Axis(tickCount=5, format=",.0f"),
                    ),
                    tooltip=[
                        alt.Tooltip("Año:N"),
                        alt.Tooltip("Eventos:Q", format=",.0f"),
                        alt.Tooltip(
                            "Magnitud promedio:Q",
                            title="Magnitud promedio",
                            format=".2f",
                        ),
                    ],
                )
                yearly_average = yearly_base.mark_line(
                    color="#2563eb",
                    point=alt.OverlayMarkDef(color="#2563eb", filled=True, size=50),
                    strokeWidth=2.5,
                ).encode(
                    x=alt.X("Año:N", sort=None),
                    y=alt.Y(
                        "Magnitud promedio:Q",
                        title="Magnitud promedio",
                        axis=alt.Axis(titleColor="#2563eb", format=".1f"),
                        scale=alt.Scale(zero=False),
                    ),
                    tooltip=[
                        alt.Tooltip("Año:N"),
                        alt.Tooltip(
                            "Magnitud promedio:Q",
                            title="Magnitud promedio",
                            format=".2f",
                        ),
                    ],
                )
                yearly_chart = alt.layer(
                    yearly_bars, yearly_average
                ).resolve_scale(y="independent").properties(
                    height=210,
                    title="Eventos y magnitud promedio por año",
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
            place = escape(str(event.get("place", "Sin ubicación")))
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
