"""
ETL - Extract & Load: Extrae datos de USGS Earthquake API y los carga
directamente a la tabla raw_earthquakes en PostgreSQL/PostGIS.

Flujo del diagrama de arquitectura:
  API Externa → Scripts Python (Extract & Load) → PostgreSQL + PostGIS (Raw)
"""
import os
from datetime import datetime

import pandas as pd
import requests
from sqlalchemy import create_engine, text

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


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


def extract_earthquakes(url: str = USGS_URL) -> pd.DataFrame:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    rows = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})

        feature_id = feature.get("id")
        rows.append({
            "id": feature_id,
            "usgs_id": feature_id,
            "mag": props.get("mag"),
            "place": props.get("place"),
            "time": datetime.utcfromtimestamp(props.get("time", 0) / 1000),
            "updated": datetime.utcfromtimestamp(props.get("updated", 0) / 1000),
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
            "longitude": geom["coordinates"][0] if geom and geom.get("coordinates") else None,
            "latitude": geom["coordinates"][1] if geom and geom.get("coordinates") else None,
            "depth": geom["coordinates"][2] if geom and geom.get("coordinates") else None,
        })

    return pd.DataFrame(rows)


def load_raw(df: pd.DataFrame, engine) -> int:
    count = 0
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("""
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
                        ingested_at = NOW()
                """),
                {k: (None if pd.isna(v) else v) for k, v in row.items()}
            )
            count += 1
    return count


def extract_and_load():
    engine = get_engine()
    df = extract_earthquakes()
    count = load_raw(df, engine)
    print(f"Extraídos y cargados {count} eventos sísmicos a raw_earthquakes")
    return {"eventos": len(df), "insertados": count}


if __name__ == "__main__":
    extract_and_load()
