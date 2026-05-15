"""
ETL - Transform & Load: Lee datos crudos desde raw_earthquakes en PostGIS,
los transforma con GeoPandas (geometrías, limpieza) y los carga en
la tabla final optimizada earthquakes.

Flujo del diagrama de arquitectura:
  PostgreSQL + PostGIS (Raw) → Pandas/GeoPandas (Transformación Espacial)
  → PostgreSQL + PostGIS (Tabla Final)
"""
import os

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from sqlalchemy import create_engine, text


def get_engine():
    db_url = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('POSTGRES_USER', 'geo_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'geo_pass')}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5433')}/"
        f"{os.getenv('POSTGRES_DB', 'geodata')}"
    )
    return create_engine(db_url)


def read_raw_earthquakes(engine) -> pd.DataFrame:
    """Lee datos crudos desde la tabla raw_earthquakes en PostGIS."""
    query = """
        SELECT usgs_id, mag, place, time, updated, magType AS magtype, tsunami, alert,
               status, sig, depth, longitude, latitude
        FROM raw_earthquakes
        WHERE longitude IS NOT NULL AND latitude IS NOT NULL
    """
    return pd.read_sql(query, engine)


def transform_to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Limpia y transforma a GeoDataFrame con geometrías Point."""
    if df.empty:
        return gpd.GeoDataFrame()

    df["mag"] = df["mag"].fillna(0)
    df["depth"] = df["depth"].fillna(0)
    df["place"] = df["place"].fillna("Unknown")
    df["status"] = df["status"].fillna("unknown")
    df["magtype"] = df["magtype"].fillna("unknown")
    df["alert"] = df["alert"].fillna("")
    df["tsunami"] = df["tsunami"].fillna(0).astype(int)
    df["sig"] = df["sig"].fillna(0).astype(int)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce")

    df = df.dropna(subset=["longitude", "latitude"])
    df = df[(df["longitude"].between(-180, 180)) & (df["latitude"].between(-90, 90))]

    df["geometry"] = df.apply(
        lambda row: Point(row["longitude"], row["latitude"]), axis=1
    )

    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    return gdf


def load_processed(gdf: gpd.GeoDataFrame, engine) -> int:
    """Carga datos transformados a la tabla final earthquakes en PostGIS."""
    if gdf.empty:
        return 0

    count = 0
    with engine.begin() as conn:
        for _, row in gdf.iterrows():
            wkt = row.geometry.wkt
            conn.execute(
                text("""
                    INSERT INTO earthquakes (
                        usgs_id, mag, place, time, updated, magType, tsunami,
                        alert, status, sig, depth, location, geom
                    ) VALUES (
                        :usgs_id, :mag, :place, :time, :updated, :magType, :tsunami,
                        :alert, :status, :sig, :depth,
                        ST_GeogFromText(:wkt),
                        ST_GeomFromText(:wkt, 4326)
                    )
                    ON CONFLICT (usgs_id) DO UPDATE SET
                        mag = EXCLUDED.mag,
                        place = EXCLUDED.place,
                        time = EXCLUDED.time,
                        updated = EXCLUDED.updated,
                        location = EXCLUDED.location,
                        geom = EXCLUDED.geom,
                        processed_at = NOW()
                """),
                {
                    "usgs_id": row.get("usgs_id"),
                    "mag": row.get("mag"),
                    "place": row.get("place"),
                    "time": row.get("time"),
                    "updated": row.get("updated"),
                    "magType": row.get("magtype"),
                    "tsunami": row.get("tsunami", 0),
                    "alert": row.get("alert", ""),
                    "status": row.get("status", "unknown"),
                    "sig": row.get("sig", 0),
                    "depth": row.get("depth", 0),
                    "wkt": wkt,
                },
            )
            count += 1
    return count


def transform_and_load():
    engine = get_engine()
    df_raw = read_raw_earthquakes(engine)
    print(f"Leidos {len(df_raw)} registros desde raw_earthquakes")

    gdf = transform_to_geodataframe(df_raw)
    print(f"Transformados {len(gdf)} registros a GeoDataFrame con geometrias")

    count = load_processed(gdf, engine)
    print(f"Cargados {count} eventos a tabla final earthquakes")
    return {"leidos": len(df_raw), "transformados": len(gdf), "cargados": count}


if __name__ == "__main__":
    transform_and_load()
