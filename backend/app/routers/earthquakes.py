from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Earthquakes"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "FastAPI Earthquakes API"}


@router.get("/earthquakes")
def list_earthquakes(
    min_mag: float = Query(0, ge=0, description="Magnitud mínima"),
    max_mag: float = Query(10, le=10, description="Magnitud máxima"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    days_back: int = Query(7, ge=1, description="Días hacia atrás"),
    db: Session = Depends(get_db),
):
    sql = text("""
        SELECT
            id, usgs_id, mag, place,
            time AT TIME ZONE 'UTC' as time,
            magType, tsunami, alert, status, sig, depth,
            ST_X(geom::geometry) AS longitude,
            ST_Y(geom::geometry) AS latitude
        FROM earthquakes
        WHERE mag BETWEEN :min_mag AND :max_mag
          AND time > NOW() - :days_back * INTERVAL '1 day'
        ORDER BY time DESC
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(sql, {
        "min_mag": min_mag,
        "max_mag": max_mag,
        "limit": limit,
        "offset": offset,
        "days_back": days_back,
    })
    rows = result.mappings().all()
    return {"count": len(rows), "results": [dict(r) for r in rows]}


@router.get("/earthquakes/radius")
def earthquakes_in_radius(
    lat: float = Query(..., description="Latitud del centro"),
    lon: float = Query(..., description="Longitud del centro"),
    dist_km: float = Query(10, ge=1, description="Radio en kilómetros"),
    min_mag: float = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Buscar sismos en un radio geográfico (consulta espacial con PostGIS)."""
    sql = text("""
        SELECT
            id, usgs_id, mag, place,
            time AT TIME ZONE 'UTC' as time,
            magType, tsunami, alert, status, sig, depth,
            ST_X(geom::geometry) AS longitude,
            ST_Y(geom::geometry) AS latitude,
            ROUND(
                ST_Distance(
                    location,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                )::numeric / 1000, 2
            ) AS distance_km
        FROM earthquakes
        WHERE mag >= :min_mag
          AND ST_DWithin(
              location,
              ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
              :dist_km * 1000
          )
        ORDER BY distance_km ASC
        LIMIT :limit
    """)
    result = db.execute(sql, {
        "lat": lat, "lon": lon, "dist_km": dist_km,
        "min_mag": min_mag, "limit": limit,
    })
    rows = result.mappings().all()
    return {
        "center": {"lat": lat, "lon": lon},
        "radius_km": dist_km,
        "count": len(rows),
        "results": [dict(r) for r in rows],
    }


@router.get("/earthquakes/stats")
def earthquake_stats(db: Session = Depends(get_db)):
    """Resumen estadístico de todos los sismos."""
    sql = text("SELECT * FROM get_earthquake_summary()")
    result = db.execute(sql)
    row = result.mappings().first()
    return dict(row) if row else {}


@router.get("/earthquakes/clusters")
def earthquake_clusters(
    radius_km: float = Query(50, ge=10, description="Radio de agrupación en km"),
    db: Session = Depends(get_db),
):
    """Agrupar sismos por proximidad geográfica (DBSCAN)."""
    sql = text("SELECT * FROM get_earthquake_clusters(:radius_km)")
    result = db.execute(sql, {"radius_km": radius_km})
    rows = result.mappings().all()
    return {"count": len(rows), "results": [dict(r) for r in rows]}


@router.get("/earthquakes/{usgs_id}")
def earthquake_detail(usgs_id: str, db: Session = Depends(get_db)):
    """Detalle de un sismo por su USGS ID."""
    sql = text("""
        SELECT
            id, usgs_id, mag, place,
            time AT TIME ZONE 'UTC' as time,
            updated AT TIME ZONE 'UTC' as updated,
            magType, tsunami, alert, status, sig, depth,
            ST_X(geom::geometry) AS longitude,
            ST_Y(geom::geometry) AS latitude
        FROM earthquakes
        WHERE usgs_id = :usgs_id
    """)
    result = db.execute(sql, {"usgs_id": usgs_id})
    row = result.mappings().first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Earthquake not found")
    return dict(row)
