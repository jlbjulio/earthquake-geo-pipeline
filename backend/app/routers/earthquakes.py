from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import text

from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["Earthquakes"])

EVENT_SORTS = {
    "recent": "time DESC, id DESC",
    "mag_desc": "mag DESC NULLS LAST, time DESC",
    "mag_asc": "mag ASC NULLS LAST, time DESC",
    "distance": "distance_km ASC, time DESC",
}


def build_time_filter(all_time: bool) -> list[str]:
    if all_time:
        return []
    return ["time > NOW() - :days_back * INTERVAL '1 day'"]


def rows_without_total(rows):
    cleaned = []
    for row in rows:
        item = dict(row)
        item.pop("total_count", None)
        cleaned.append(item)
    return cleaned


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "FastAPI Earthquakes API"}


@router.get("/earthquakes")
def list_earthquakes(
    min_mag: float = Query(0, ge=0, description="Magnitud minima"),
    max_mag: float = Query(10, le=10, description="Magnitud maxima"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    days_back: int = Query(7, ge=1, description="Dias hacia atras"),
    all_time: bool = Query(False, description="Consultar todo lo cargado"),
    sort: str = Query("recent", description="recent, mag_desc o mag_asc"),
    db: Session = Depends(get_db),
):
    filters = ["mag BETWEEN :min_mag AND :max_mag", *build_time_filter(all_time)]
    where_clause = " AND ".join(filters)
    order_by = EVENT_SORTS.get(sort, EVENT_SORTS["recent"])
    if order_by == EVENT_SORTS["distance"]:
        order_by = EVENT_SORTS["recent"]

    sql = text(f"""
        WITH filtered AS (
            SELECT
                id, usgs_id, mag, place, time,
                magType, tsunami, alert, status, sig, depth, geom
            FROM earthquakes
            WHERE {where_clause}
        )
        SELECT
            id, usgs_id, mag, place,
            time AT TIME ZONE 'UTC' as time,
            magType AS "magType", tsunami, alert, status, sig, depth,
            ST_X(geom::geometry) AS longitude,
            ST_Y(geom::geometry) AS latitude,
            COUNT(*) OVER()::INTEGER AS total_count
        FROM filtered
        ORDER BY {order_by}
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
    total_count = rows[0]["total_count"] if rows else 0
    return {
        "count": len(rows),
        "total_count": total_count,
        "results": rows_without_total(rows),
    }


@router.get("/earthquakes/radius")
def earthquakes_in_radius(
    lat: float = Query(..., description="Latitud del centro"),
    lon: float = Query(..., description="Longitud del centro"),
    dist_km: float = Query(10, ge=1, description="Radio en kilometros"),
    min_mag: float = Query(0, ge=0),
    max_mag: float = Query(10, le=10),
    days_back: int = Query(30, ge=1),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    all_time: bool = Query(False, description="Consultar todo lo cargado"),
    sort: str = Query("distance", description="distance, recent, mag_desc o mag_asc"),
    db: Session = Depends(get_db),
):
    """Buscar sismos en un radio geografico con PostGIS."""
    filters = [
        "mag BETWEEN :min_mag AND :max_mag",
        *build_time_filter(all_time),
        """
        ST_DWithin(
            location,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :dist_km * 1000
        )
        """,
    ]
    where_clause = " AND ".join(filters)
    order_by = EVENT_SORTS.get(sort, EVENT_SORTS["distance"])

    sql = text(f"""
        WITH filtered AS (
            SELECT
                id, usgs_id, mag, place, time,
                magType, tsunami, alert, status, sig, depth, geom,
                ROUND(
                    ST_Distance(
                        location,
                        ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                    )::numeric / 1000, 2
                ) AS distance_km
            FROM earthquakes
            WHERE {where_clause}
        )
        SELECT
            id, usgs_id, mag, place,
            time AT TIME ZONE 'UTC' as time,
            magType AS "magType", tsunami, alert, status, sig, depth,
            ST_X(geom::geometry) AS longitude,
            ST_Y(geom::geometry) AS latitude,
            distance_km,
            COUNT(*) OVER()::INTEGER AS total_count
        FROM filtered
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(sql, {
        "lat": lat,
        "lon": lon,
        "dist_km": dist_km,
        "min_mag": min_mag,
        "max_mag": max_mag,
        "days_back": days_back,
        "limit": limit,
        "offset": offset,
    })
    rows = result.mappings().all()
    total_count = rows[0]["total_count"] if rows else 0
    return {
        "center": {"lat": lat, "lon": lon},
        "radius_km": dist_km,
        "count": len(rows),
        "total_count": total_count,
        "results": rows_without_total(rows),
    }


@router.get("/earthquakes/stats")
def earthquake_stats(db: Session = Depends(get_db)):
    """Resumen estadistico de todos los sismos."""
    sql = text("SELECT * FROM get_earthquake_summary()")
    result = db.execute(sql)
    row = result.mappings().first()
    return dict(row) if row else {}


@router.get("/earthquakes/analysis")
def earthquake_analysis(
    min_mag: float = Query(0, ge=0),
    max_mag: float = Query(10, le=10),
    days_back: int = Query(30, ge=1),
    all_time: bool = Query(False, description="Consultar todo lo cargado"),
    lat: float | None = Query(None),
    lon: float | None = Query(None),
    dist_km: float | None = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    """Resumen analitico agregado en PostGIS para evitar traer datos pesados al dashboard."""
    filters = [
        "mag BETWEEN :min_mag AND :max_mag",
        *build_time_filter(all_time),
    ]
    params = {
        "min_mag": min_mag,
        "max_mag": max_mag,
        "days_back": days_back,
    }

    if lat is not None and lon is not None and dist_km is not None:
        filters.append("""
            ST_DWithin(
                location,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :dist_km * 1000
            )
        """)
        params.update({"lat": lat, "lon": lon, "dist_km": dist_km})

    where_clause = " AND ".join(filters)
    filtered_cte = f"""
        WITH filtered AS (
            SELECT
                id,
                usgs_id,
                mag,
                place,
                time,
                depth,
                geom,
                CASE
                    WHEN mag < 2 THEN 'Micro'
                    WHEN mag < 4 THEN 'Leve'
                    WHEN mag < 6 THEN 'Fuerte'
                    ELSE 'Severo'
                END AS category,
                CASE
                    WHEN place IS NULL OR TRIM(place) = '' THEN 'Sin ubicacion'
                    WHEN place LIKE '%,%' THEN TRIM(REGEXP_REPLACE(place, '^.*,\\s*', ''))
                    WHEN POSITION(' of ' IN place) > 0 THEN TRIM(REGEXP_REPLACE(place, '^.* of\\s+', ''))
                    ELSE place
                END AS region
            FROM earthquakes
            WHERE {where_clause}
        )
    """

    summary_sql = text(f"""
        {filtered_cte}
        SELECT
            COUNT(*)::INTEGER AS total_events,
            ROUND(AVG(mag)::NUMERIC, 2)::FLOAT AS avg_magnitude,
            ROUND(AVG(depth)::NUMERIC, 2)::FLOAT AS avg_depth,
            ROUND(MAX(mag)::NUMERIC, 2)::FLOAT AS max_magnitude,
            ROUND(MIN(mag)::NUMERIC, 2)::FLOAT AS min_magnitude,
            MAX(time) AT TIME ZONE 'UTC' AS last_update
        FROM filtered
    """)
    category_sql = text(f"""
        {filtered_cte}
        SELECT category, COUNT(*)::INTEGER AS events
        FROM filtered
        GROUP BY category
    """)
    region_sql = text(f"""
        {filtered_cte}
        SELECT
            region,
            COUNT(*)::INTEGER AS events,
            ROUND(AVG(mag)::NUMERIC, 2)::FLOAT AS avg_magnitude
        FROM filtered
        GROUP BY region
        ORDER BY events DESC, avg_magnitude DESC
        LIMIT 8
    """)
    depth_sql = text(f"""
        {filtered_cte}
        SELECT
            CASE
                WHEN depth < 70 THEN 'Superficial'
                WHEN depth < 300 THEN 'Intermedia'
                ELSE 'Profunda'
            END AS depth_group,
            COUNT(*)::INTEGER AS events,
            ROUND(AVG(mag)::NUMERIC, 2)::FLOAT AS avg_magnitude
        FROM filtered
        GROUP BY depth_group
        ORDER BY events DESC
    """)
    strongest_sql = text(f"""
        {filtered_cte}
        SELECT
            usgs_id,
            ROUND(mag::NUMERIC, 2)::FLOAT AS mag,
            place,
            time AT TIME ZONE 'UTC' AS time,
            ROUND(depth::NUMERIC, 2)::FLOAT AS depth,
            ST_X(geom::geometry) AS longitude,
            ST_Y(geom::geometry) AS latitude
        FROM filtered
        ORDER BY mag DESC, time DESC
        LIMIT 5
    """)
    daily_sql = text(f"""
        {filtered_cte}
        SELECT
            TO_CHAR(date_trunc('day', time AT TIME ZONE 'UTC'), 'YYYY-MM-DD') AS period,
            COUNT(*)::INTEGER AS events,
            ROUND(AVG(mag)::NUMERIC, 2)::FLOAT AS avg_magnitude
        FROM filtered
        GROUP BY date_trunc('day', time AT TIME ZONE 'UTC')
        ORDER BY date_trunc('day', time AT TIME ZONE 'UTC')
    """)
    monthly_sql = text(f"""
        {filtered_cte}
        SELECT
            TO_CHAR(date_trunc('month', time AT TIME ZONE 'UTC'), 'YYYY-MM') AS period,
            COUNT(*)::INTEGER AS events,
            ROUND(AVG(mag)::NUMERIC, 2)::FLOAT AS avg_magnitude
        FROM filtered
        GROUP BY date_trunc('month', time AT TIME ZONE 'UTC')
        ORDER BY date_trunc('month', time AT TIME ZONE 'UTC')
    """)
    yearly_sql = text(f"""
        {filtered_cte}
        SELECT
            TO_CHAR(date_trunc('year', time AT TIME ZONE 'UTC'), 'YYYY') AS period,
            COUNT(*)::INTEGER AS events,
            ROUND(AVG(mag)::NUMERIC, 2)::FLOAT AS avg_magnitude
        FROM filtered
        GROUP BY date_trunc('year', time AT TIME ZONE 'UTC')
        ORDER BY date_trunc('year', time AT TIME ZONE 'UTC')
    """)

    summary = db.execute(summary_sql, params).mappings().first() or {}
    categories = {label: 0 for label in ["Micro", "Leve", "Fuerte", "Severo"]}
    for row in db.execute(category_sql, params).mappings().all():
        categories[row["category"]] = row["events"]

    return {
        "filters": {
            "min_mag": min_mag,
            "max_mag": max_mag,
            "days_back": days_back,
            "all_time": all_time,
            "radius": (
                {"lat": lat, "lon": lon, "dist_km": dist_km}
                if lat is not None and lon is not None and dist_km is not None
                else None
            ),
        },
        "summary": dict(summary),
        "category_counts": categories,
        "top_regions": [dict(row) for row in db.execute(region_sql, params).mappings().all()],
        "depth_groups": [dict(row) for row in db.execute(depth_sql, params).mappings().all()],
        "strongest_events": [dict(row) for row in db.execute(strongest_sql, params).mappings().all()],
        "daily_counts": [dict(row) for row in db.execute(daily_sql, params).mappings().all()],
        "monthly_counts": [dict(row) for row in db.execute(monthly_sql, params).mappings().all()],
        "yearly_counts": [dict(row) for row in db.execute(yearly_sql, params).mappings().all()],
    }


@router.get("/earthquakes/clusters")
def earthquake_clusters(
    radius_km: float = Query(50, ge=10, description="Radio de agrupacion en km"),
    db: Session = Depends(get_db),
):
    """Agrupar sismos por proximidad geografica (DBSCAN)."""
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
            magType AS "magType", tsunami, alert, status, sig, depth,
            ST_X(geom::geometry) AS longitude,
            ST_Y(geom::geometry) AS latitude
        FROM earthquakes
        WHERE usgs_id = :usgs_id
    """)
    result = db.execute(sql, {"usgs_id": usgs_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Earthquake not found")
    return dict(row)
