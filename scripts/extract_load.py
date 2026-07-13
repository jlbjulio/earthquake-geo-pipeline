"""
ETL - Extract & Load: Extrae datos de USGS Earthquake API y los carga
directamente a la tabla raw_earthquakes en PostgreSQL/PostGIS.

Flujo del diagrama de arquitectura:
  API Externa → Scripts Python (Extract & Load) → PostgreSQL + PostGIS (Raw)
"""
import os
from datetime import datetime, timezone

import pandas as pd
import requests
from sqlalchemy.engine.create import create_engine
from sqlalchemy.sql.expression import text

DEFAULT_USGS_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
)


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


def extract_earthquakes(url: str | None = None) -> pd.DataFrame:
    url = url or os.getenv("USGS_FEED_URL", DEFAULT_USGS_URL)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    rows = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coordinates = geom.get("coordinates") if geom else None

        feature_id = feature.get("id")
        event_time = props.get("time")
        updated_time = props.get("updated") or event_time
        if not feature_id or not event_time or not coordinates or len(coordinates) < 3:
            continue
        rows.append({
            "id": feature_id,
            "usgs_id": feature_id,
            "mag": props.get("mag"),
            "place": props.get("place"),
            "time": datetime.fromtimestamp(event_time / 1000, tz=timezone.utc),
            "updated": datetime.fromtimestamp(updated_time / 1000, tz=timezone.utc),
            "tz": props.get("tz"),
            "url": props.get("url"),
            "detail": props.get("detail"),
            "felt": props.get("felt"),
            "cdi": props.get("cdi"),
            "mmi": props.get("mmi"),
            "alert": props.get("alert"),
            "status": props.get("status"),
            "tsunami": props.get("tsunami", 0),
            "sig": props.get("sig"),
            "net": props.get("net"),
            "code": props.get("code"),
            "ids": props.get("ids"),
            "sources": props.get("sources"),
            "types": props.get("types"),
            "nst": props.get("nst"),
            "dmin": props.get("dmin"),
            "rms": props.get("rms"),
            "gap": props.get("gap"),
            "magType": props.get("magType"),
            "geometry_type": geom.get("type") if geom else None,
            "longitude": coordinates[0],
            "latitude": coordinates[1],
            "depth": coordinates[2],
        })

    return pd.DataFrame(rows)


def load_raw(df: pd.DataFrame, engine) -> int:
    if df.empty:
        return 0

    records = [
        {key: (None if pd.isna(value) else value) for key, value in row.items()}
        for row in df.to_dict(orient="records")
    ]

    sql = text("""
        INSERT INTO raw_earthquakes (
            id, usgs_id, mag, place, time, updated, tz, url, detail,
            felt, cdi, mmi, alert, status, tsunami, sig, net, code,
            ids, sources, types, nst, dmin, rms, gap, magType,
            geometry_type, longitude, latitude, depth
        ) VALUES (
            :id, :usgs_id, :mag, :place, :time, :updated, :tz, :url, :detail,
            :felt, :cdi, :mmi, :alert, :status, :tsunami, :sig, :net, :code,
            :ids, :sources, :types, :nst, :dmin, :rms, :gap, :magType,
            :geometry_type, :longitude, :latitude, :depth
        )
        ON CONFLICT (usgs_id) DO UPDATE SET
            mag = EXCLUDED.mag,
            place = EXCLUDED.place,
            time = EXCLUDED.time,
            updated = EXCLUDED.updated,
            alert = EXCLUDED.alert,
            status = EXCLUDED.status,
            tsunami = EXCLUDED.tsunami,
            sig = EXCLUDED.sig,
            magType = EXCLUDED.magType,
            geometry_type = EXCLUDED.geometry_type,
            longitude = EXCLUDED.longitude,
            latitude = EXCLUDED.latitude,
            depth = EXCLUDED.depth,
            ingested_at = NOW()
    """)

    with engine.begin() as conn:
        conn.execute(sql, records)
    return len(records)


def extract_and_load():
    engine = get_engine()
    df = extract_earthquakes()
    count = load_raw(df, engine)
    print(f"Extraídos y cargados {count} eventos sísmicos a raw_earthquakes")
    return {"eventos": len(df), "insertados": count}


if __name__ == "__main__":
    extract_and_load()
