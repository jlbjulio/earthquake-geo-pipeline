-- =============================================
-- Proyecto Semestral - Tópicos Especiales II
-- Esquema de Base de Datos Espacial
-- PostgreSQL + PostGIS
-- =============================================

-- Habilitar extensión PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- =============================================
-- Tabla: raw_earthquakes
-- Datos crudos tal como llegan de la API
-- =============================================
CREATE TABLE IF NOT EXISTS raw_earthquakes (
    id              VARCHAR(50) PRIMARY KEY,
    usgs_id         VARCHAR(100) UNIQUE NOT NULL,
    mag             NUMERIC(6, 2),
    place           TEXT,
    time            TIMESTAMPTZ,
    updated         TIMESTAMPTZ,
    tz              INTEGER,
    url             TEXT,
    detail          TEXT,
    felt            INTEGER,
    cdi             NUMERIC(4, 2),
    mmi             NUMERIC(4, 2),
    alert           VARCHAR(20),
    status          VARCHAR(20),
    tsunami         INTEGER,
    sig             INTEGER,
    net             VARCHAR(10),
    code            VARCHAR(30),
    ids             TEXT,
    sources         TEXT,
    types           TEXT,
    nst             INTEGER,
    dmin            NUMERIC(10, 4),
    rms             NUMERIC(10, 4),
    gap             NUMERIC(8, 2),
    magType         VARCHAR(20),
    geometry_type   VARCHAR(20),
    longitude       NUMERIC(10, 6),
    latitude        NUMERIC(10, 6),
    depth           NUMERIC(10, 2),
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- Tabla: earthquakes (datos procesados con geometría espacial)
-- Tabla final optimizada para consultas geoespaciales
-- =============================================
CREATE TABLE IF NOT EXISTS earthquakes (
    id              SERIAL PRIMARY KEY,
    usgs_id         VARCHAR(100) UNIQUE NOT NULL,
    mag             NUMERIC(6, 2),
    place           TEXT,
    time            TIMESTAMPTZ,
    updated         TIMESTAMPTZ,
    magType         VARCHAR(20),
    tsunami         INTEGER DEFAULT 0,
    alert           VARCHAR(20),
    status          VARCHAR(20),
    sig             INTEGER,
    depth           NUMERIC(10, 2),
    location        GEOGRAPHY(Point, 4326),
    geom            GEOMETRY(Point, 4326),
    processed_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Índices espaciales para consultas geográficas rápidas
CREATE INDEX IF NOT EXISTS idx_earthquakes_location
    ON earthquakes USING GIST (location);

CREATE INDEX IF NOT EXISTS idx_earthquakes_geom
    ON earthquakes USING GIST (geom);

-- Índices para filtros comunes
CREATE INDEX IF NOT EXISTS idx_earthquakes_mag
    ON earthquakes (mag DESC);

CREATE INDEX IF NOT EXISTS idx_earthquakes_time
    ON earthquakes (time DESC);

CREATE INDEX IF NOT EXISTS idx_earthquakes_time_mag
    ON earthquakes (time DESC, mag DESC);

CREATE INDEX IF NOT EXISTS idx_earthquakes_updated
    ON earthquakes (updated DESC);

CREATE INDEX IF NOT EXISTS idx_earthquakes_tsunami
    ON earthquakes (tsunami);

CREATE INDEX IF NOT EXISTS idx_raw_earthquakes_updated
    ON raw_earthquakes (updated DESC);

CREATE INDEX IF NOT EXISTS idx_raw_earthquakes_time
    ON raw_earthquakes (time DESC);

-- =============================================
-- Tabla: tsunami_events
-- Vista materializada para eventos con tsunami
-- =============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS tsunami_events AS
SELECT
    id,
    usgs_id,
    mag,
    place,
    time,
    depth,
    location,
    geom
FROM earthquakes
WHERE tsunami = 1
ORDER BY time DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tsunami_events_id
    ON tsunami_events (id);

-- =============================================
-- Función: agrupar sismos por proximidad geográfica
-- Devuelve clusters de sismos en un radio dado (km)
-- =============================================
CREATE OR REPLACE FUNCTION get_earthquake_clusters(
    radius_km NUMERIC DEFAULT 50
)
RETURNS TABLE(
    cluster_id      INTEGER,
    centroid_lat    NUMERIC,
    centroid_lng    NUMERIC,
    earthquake_count BIGINT,
    avg_mag         NUMERIC,
    max_mag         NUMERIC
)
LANGUAGE SQL
STABLE
AS $$
    WITH clusters AS (
        SELECT
            ST_ClusterDBSCAN(geom, radius_km / 111.32, 1)
                OVER () AS cid,
            mag,
            geom
        FROM earthquakes
        WHERE time > NOW() - INTERVAL '7 days'
    )
    SELECT
        cid AS cluster_id,
        ROUND(AVG(ST_Y(geom))::NUMERIC, 4) AS centroid_lat,
        ROUND(AVG(ST_X(geom))::NUMERIC, 4) AS centroid_lng,
        COUNT(*)::BIGINT AS earthquake_count,
        ROUND(AVG(mag)::NUMERIC, 2) AS avg_mag,
        ROUND(MAX(mag)::NUMERIC, 2) AS max_mag
    FROM clusters
    WHERE cid IS NOT NULL
    GROUP BY cid
    ORDER BY earthquake_count DESC;
$$;

-- =============================================
-- Función: obtener resumen estadístico
-- =============================================
CREATE OR REPLACE FUNCTION get_earthquake_summary()
RETURNS TABLE(
    total_events        BIGINT,
    avg_magnitude       NUMERIC,
    max_magnitude       NUMERIC,
    min_magnitude       NUMERIC,
    total_tsunami       BIGINT,
    last_update         TIMESTAMPTZ,
    most_active_place   TEXT
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        COUNT(*)::BIGINT AS total_events,
        ROUND(AVG(mag)::NUMERIC, 2) AS avg_magnitude,
        ROUND(MAX(mag)::NUMERIC, 2) AS max_magnitude,
        ROUND(MIN(mag)::NUMERIC, 2) AS min_magnitude,
        SUM(tsunami)::BIGINT AS total_tsunami,
        MAX(time) AS last_update,
        (SELECT place FROM earthquakes
         ORDER BY mag DESC LIMIT 1) AS most_active_place
    FROM earthquakes;
$$;
