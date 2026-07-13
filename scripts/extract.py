"""
ETL - Extract: Extrae datos sísmicos desde la API de USGS.
API: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
"""
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

def extract_earthquakes(url: str = USGS_URL) -> pd.DataFrame:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    rows = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})

        rows.append({
            "usgs_id": feature.get("id"),
            "mag": props.get("mag"),
            "place": props.get("place"),
            "time": datetime.fromtimestamp(props.get("time", 0) / 1000, tz=timezone.utc),
            "updated": datetime.fromtimestamp(props.get("updated", 0) / 1000, tz=timezone.utc),
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


if __name__ == "__main__":
    df = extract_earthquakes()
    output_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/raw_earthquakes.json"
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    df.to_json(output_path, orient="records", date_format="iso")
    print(f"Extraídos {len(df)} eventos sísmicos -> {output_path}")
