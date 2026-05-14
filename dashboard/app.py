import os
import time

import folium
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Dashboard Sísmico - GeoEspacial",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Dashboard de Monitoreo Sísmico")
st.markdown("Datos en tiempo real del **USGS Earthquake Catalog** vía API propia con **PostGIS**.")


def fetch_data(endpoint: str, params: dict = None) -> dict:
    try:
        resp = requests.get(f"{API_BASE_URL}/api/v1/{endpoint}",
                            params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Error conectando con la API: {e}")
        return {"count": 0, "results": []}


# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Filtros")

    min_mag = st.slider("Magnitud mínima", 0.0, 9.0, 1.0, 0.1)
    days_back = st.slider("Días hacia atrás", 1, 30, 7)

    st.subheader("🔍 Búsqueda por radio")
    use_radius = st.checkbox("Activar búsqueda radial")
    lat = st.number_input("Latitud", value=25.0, format="%.4f")
    lon = st.number_input("Longitud", value=-100.0, format="%.4f")
    dist_km = st.slider("Radio (km)", 10, 1000, 200)

    st.divider()
    auto_refresh = st.checkbox("Auto-refresh cada 30s", value=True)
    if auto_refresh:
        st.info("El dashboard se actualizará automáticamente.")

st.sidebar.divider()
if st.sidebar.button("🔄 Refrescar ahora"):
    st.rerun()


# ── Layout: KPIs ──
col1, col2, col3, col4 = st.columns(4)

# Estadísticas
stats = fetch_data("earthquakes/stats")

with col1:
    st.metric("Total de Eventos", stats.get("total_events", "N/A"))
with col2:
    mag_avg = stats.get("avg_magnitude", "N/A")
    st.metric("Magnitud Promedio", mag_avg)
with col3:
    st.metric("Magnitud Máxima", stats.get("max_magnitude", "N/A"))
with col4:
    st.metric("Eventos con Tsunami", stats.get("total_tsunami", "N/A"))


# ── Mapa interactivo ──
st.subheader("🗺️ Mapa de Eventos Sísmicos")

if use_radius:
    data = fetch_data("earthquakes/radius", {
        "lat": lat, "lon": lon,
        "dist_km": dist_km,
        "min_mag": min_mag,
        "limit": 500,
    })
else:
    data = fetch_data("earthquakes", {
        "min_mag": min_mag,
        "days_back": days_back,
        "limit": 500,
    })

results = data.get("results", [])

if results:
    # Crear mapa centrado en el promedio de coordenadas
    avg_lat = sum(r["latitude"] for r in results) / len(results)
    avg_lon = sum(r["longitude"] for r in results) / len(results)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=3,
                   tiles="CartoDB positron")

    for eq in results:
        mag = eq.get("mag", 0)
        color = (
            "green" if mag < 2
            else "yellow" if mag < 4
            else "orange" if mag < 6
            else "red"
        )
        radius = max(3, min(mag * 3, 30))

        folium.CircleMarker(
            location=[eq["latitude"], eq["longitude"]],
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(
                f"<b>{eq.get('place', 'Unknown')}</b><br>"
                f"Magnitud: {mag}<br>"
                f"Profundidad: {eq.get('depth', 'N/A')} km<br>"
                f"Hora: {eq.get('time', 'N/A')}<br>"
                f"Tsunami: {'⚠️ Sí' if eq.get('tsunami') else 'No'}<br>"
                f"<a href='/api/v1/earthquakes/{eq['usgs_id']}' target='_blank'>Ver detalle</a>"
            ),
        ).add_to(m)

    # Si es búsqueda radial, mostrar círculo de radio
    if use_radius:
        folium.Circle(
            location=[lat, lon],
            radius=dist_km * 1000,
            color="blue",
            fill=False,
            weight=2,
            dash_array="5, 5",
        ).add_to(m)

    st_folium(m, width=None, height=500)
else:
    st.warning("No se encontraron eventos sísmicos con los filtros actuales.")


# ── Tabla de datos ──
st.subheader("📋 Últimos Eventos")

if results:
    df = pd.DataFrame(results)
    df = df.drop(columns=["usgs_id"], errors="ignore")
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["time"] = df["time"].dt.strftime("%Y-%m-%d %H:%M UTC")

    # Formatear columnas
    col_order = ["mag", "place", "time", "depth", "latitude", "longitude",
                 "magType", "tsunami", "alert", "status"]
    col_order = [c for c in col_order if c in df.columns]
    st.dataframe(df[col_order], use_container_width=True, hide_index=True)
else:
    st.info("Sin datos para mostrar.")


# ── Clusters ──
st.subheader("🔘 Clusters Sísmicos (DBSCAN)")
cluster_data = fetch_data("earthquakes/clusters", {"radius_km": 100})
clusters = cluster_data.get("results", [])

if clusters:
    df_clusters = pd.DataFrame(clusters)
    df_clusters.columns = [
        "Cluster ID", "Latitud Centro", "Longitud Centro",
        "Conteo", "Mag Promedio", "Mag Máxima"
    ]
    st.dataframe(df_clusters, use_container_width=True, hide_index=True)
else:
    st.info("No se encontraron clusters.")


# ── Gráfico de magnitud ──
st.subheader("📈 Distribución de Magnitudes")
if results:
    df_plot = pd.DataFrame(results)
    st.bar_chart(df_plot["mag"].value_counts().sort_index())


# Auto-refresh
if auto_refresh:
    time.sleep(30)
    st.rerun()
