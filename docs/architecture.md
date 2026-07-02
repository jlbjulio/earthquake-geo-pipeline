# Documento de Especificacion Tecnica

**Integrantes:** Julio Lara (8-997-2325), Joseph Batista (8-1009-1500)

## Descripcion General

Este proyecto implementa un pipeline end-to-end para datos geoespaciales de sismos:

1. USGS Earthquake API publica eventos en formato GeoJSON.
2. Mage AI orquesta el pipeline `earthquake_pipeline`.
3. `extract_load.py` consulta USGS y carga datos crudos en `raw_earthquakes`.
4. `transform_load.py` limpia datos y genera geometrias `Point`.
5. PostgreSQL + PostGIS almacena la tabla final `earthquakes`.
6. FastAPI expone endpoints REST con consultas espaciales.
7. Streamlit + Folium visualiza KPIs, mapa, tabla y clusters.

## Stack Tecnologico

| Componente      | Tecnologia                  |
| --------------- | --------------------------- |
| Orquestacion    | Mage AI                     |
| Base de datos   | PostgreSQL 16 + PostGIS 3.4 |
| Procesamiento   | Python, Pandas, GeoPandas   |
| Backend/API     | FastAPI, Uvicorn, SQLAlchemy |
| Dashboard       | Streamlit, Folium           |
| Infraestructura | Docker, Docker Compose      |

## Diagrama de Arquitectura

```text
USGS Earthquake API
        |
        v
Mage AI: earthquake_pipeline
        |
        v
scripts/extract_load.py
        |
        v
PostGIS: raw_earthquakes
        |
        v
scripts/transform_load.py
        |
        v
PostGIS: earthquakes + indices GIST
        |
        v
FastAPI: /api/v1/*
        |
        v
Streamlit + Folium
```

## Puertos

| Servicio   | Puerto host | URL                        |
| ---------- | ----------- | -------------------------- |
| PostGIS    | 5433        | localhost:5433             |
| Mage AI    | 6789        | http://localhost:6789      |
| FastAPI    | 8001        | http://localhost:8001      |
| Swagger UI | 8001        | http://localhost:8001/docs |
| Streamlit  | 8501        | http://localhost:8501      |

El backend usa `8001` en el host para evitar choques con otros proyectos FastAPI que suelen usar `8000`. Dentro de Docker, Streamlit se comunica con `http://backend:8000`.

## Pipeline de Mage AI

Pipeline: `earthquake_pipeline`

| Bloque | Tipo | Script | Funcion |
| ------ | ---- | ------ | ------- |
| `extract_and_load` | Data Loader | `scripts/extract_load.py` | Consulta USGS y hace upsert en `raw_earthquakes` |
| `transform_and_load` | Data Exporter | `scripts/transform_load.py` | Genera geometrias y hace upsert en `earthquakes` |

Trigger: cada 12 horas.

Ejecucion manual:

```bash
docker compose exec -w /home/src mage mage run earthquake_geo_pipeline earthquake_pipeline
```

## Modelo de Datos

### `raw_earthquakes`

Tabla cruda con los campos principales de USGS:

| Campo | Tipo | Uso |
| ----- | ---- | --- |
| `id` | varchar | ID de la feature |
| `usgs_id` | varchar unique | Clave de upsert |
| `mag` | numeric | Magnitud |
| `place` | text | Lugar reportado |
| `time` | timestamptz | Hora del evento |
| `longitude` | numeric | Longitud |
| `latitude` | numeric | Latitud |
| `depth` | numeric | Profundidad |
| `ingested_at` | timestamptz | Fecha de carga |

### `earthquakes`

Tabla final optimizada:

| Campo | Tipo | Uso |
| ----- | ---- | --- |
| `id` | serial primary key | ID interno |
| `usgs_id` | varchar unique | Clave USGS |
| `mag` | numeric | Magnitud |
| `place` | text | Lugar |
| `time` | timestamptz | Hora del evento |
| `location` | geography(Point, 4326) | Distancias geodesicas |
| `geom` | geometry(Point, 4326) | Clustering e indices espaciales |
| `processed_at` | timestamptz | Fecha de procesamiento |

## Indices y Funciones Espaciales

| Objeto | Proposito |
| ------ | --------- |
| `idx_earthquakes_location` | Busqueda radial con `ST_DWithin` |
| `idx_earthquakes_geom` | Operaciones geometricas y DBSCAN |
| `idx_earthquakes_mag` | Filtros por magnitud |
| `idx_earthquakes_time` | Orden temporal |
| `get_earthquake_summary()` | KPIs agregados |
| `get_earthquake_clusters(radius_km)` | Clusters espaciales |

## Endpoints

| Metodo | Endpoint | Descripcion |
| ------ | -------- | ----------- |
| GET | `/api/v1/health` | Estado del backend |
| GET | `/api/v1/earthquakes` | Lista filtrable |
| GET | `/api/v1/earthquakes/radius` | Busqueda por radio |
| GET | `/api/v1/earthquakes/stats` | Estadisticas |
| GET | `/api/v1/earthquakes/clusters` | Clusters DBSCAN |
| GET | `/api/v1/earthquakes/{usgs_id}` | Detalle por evento |

## Verificacion

```bash
docker compose ps
curl http://localhost:8001/api/v1/health
curl http://localhost:8001/api/v1/earthquakes/stats
```
