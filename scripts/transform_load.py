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
from sqlalchemy.engine.create import create_engine
from sqlalchemy.sql.expression import text


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


def read_raw_earthquakes(engine, incremental: bool = True) -> pd.DataFrame:
    """Lee datos crudos; por defecto solo eventos nuevos o actualizados."""
    if incremental:
        query = text("""
            SELECT r.usgs_id, r.mag, r.place, r.time, r.updated,
                   r.magType AS magtype, r.tsunami, r.alert,
                   r.status, r.sig, r.depth, r.longitude, r.latitude
            FROM raw_earthquakes r
            LEFT JOIN earthquakes e ON e.usgs_id = r.usgs_id
            WHERE r.longitude IS NOT NULL
              AND r.latitude IS NOT NULL
              AND (
                  e.usgs_id IS NULL
                  OR COALESCE(r.updated, r.time, 'epoch'::timestamptz)
                     > COALESCE(e.updated, e.time, 'epoch'::timestamptz)
              )
        """)
    else:
        query = text("""
            SELECT usgs_id, mag, place, time, updated, magType AS magtype, tsunami, alert,
                   status, sig, depth, longitude, latitude
            FROM raw_earthquakes
            WHERE longitude IS NOT NULL AND latitude IS NOT NULL
        """)
    with engine.connect() as conn:
        return pd.read_sql_query(query, conn)


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

    records = []
    for _, row in gdf.iterrows():
        records.append({
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
            "wkt": row.geometry.wkt,
        })

    sql = text("""
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
            magType = EXCLUDED.magType,
            tsunami = EXCLUDED.tsunami,
            alert = EXCLUDED.alert,
            status = EXCLUDED.status,
            sig = EXCLUDED.sig,
            depth = EXCLUDED.depth,
            location = EXCLUDED.location,
            geom = EXCLUDED.geom,
            processed_at = NOW()
    """)

    with engine.begin() as conn:
        conn.execute(sql, records)
        conn.execute(text("REFRESH MATERIALIZED VIEW tsunami_events"))
    return len(records)


def transform_and_load():
    engine = get_engine()
    full_reprocess = os.getenv("FULL_REPROCESS", "false").lower() in {"1", "true", "yes"}
    incremental = not full_reprocess
    df_raw = read_raw_earthquakes(engine, incremental=incremental)
    mode = "incrementales" if incremental else "totales"
    print(f"Leidos {len(df_raw)} registros {mode} desde raw_earthquakes")

    gdf = transform_to_geodataframe(df_raw)
    print(f"Transformados {len(gdf)} registros a GeoDataFrame con geometrias")

    count = load_processed(gdf, engine)
    print(f"Cargados {count} eventos a tabla final earthquakes")
    return {
        "modo": mode,
        "leidos": len(df_raw),
        "transformados": len(gdf),
        "cargados": count,
    }


if __name__ == "__main__":
    transform_and_load()
