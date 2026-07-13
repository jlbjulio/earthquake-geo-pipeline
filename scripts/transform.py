"""
ETL - Transform: Limpia, transforma datos sísmicos y construye geometrías.
Convierte coordenadas a objetos Point de PostGIS usando GeoPandas.
"""
import os
import sys

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


def transform_earthquakes(input_path: str) -> gpd.GeoDataFrame:
    df = pd.read_json(input_path)

    if df.empty:
        return gpd.GeoDataFrame()

    # Limpiar valores nulos en columnas críticas
    # Una magnitud o profundidad desconocida no equivale científicamente a cero.
    df["mag"] = pd.to_numeric(df["mag"], errors="coerce")
    df["depth"] = pd.to_numeric(df["depth"], errors="coerce")
    df["place"] = df["place"].fillna("Unknown")
    df["status"] = df["status"].fillna("unknown")
    df["magType"] = df["magType"].fillna("unknown")
    df["alert"] = df["alert"].fillna("")
    df["tsunami"] = df["tsunami"].fillna(0).astype(int)
    df["sig"] = df["sig"].fillna(0).astype(int)

    # Convertir columnas temporales
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce")

    # Filtrar registros con coordenadas válidas
    df = df.dropna(subset=["longitude", "latitude"])
    df = df[(df["longitude"].between(-180, 180)) & (df["latitude"].between(-90, 90))]

    # Crear geometría Point con Shapely
    df["geometry"] = df.apply(
        lambda row: Point(row["longitude"], row["latitude"]), axis=1
    )

    # Convertir a GeoDataFrame con CRS WGS84 (EPSG:4326)
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    return gdf


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/raw_earthquakes.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/clean_earthquakes.geojson"

    gdf = transform_earthquakes(input_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Guardar como GeoJSON
    gdf.to_file(output_path, driver="GeoJSON")
    print(f"Transformados {len(gdf)} eventos -> {output_path}")
