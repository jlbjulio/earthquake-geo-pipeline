# Documento de Especificación Técnica

**Integrantes:** Julio Lara (8-997-2325), Joseph Batista (8-1009-1500)

## Arquitectura del Proyecto

### Descripción General

Pipeline E2E de datos geoespaciales que integra:

1. **Fuente**: USGS Earthquake API (GeoJSON en tiempo real)
2. **Orquestación**: Mage AI programa la ejecución cada 12 horas
3. **Extracción y Carga (Raw)**: Scripts Python consultan API y almacenan datos crudos directamente en PostgreSQL/PostGIS
4. **Transformación**: GeoPandas lee datos crudos desde PostGIS, limpia, valida y convierte coordenadas a geometrías Point
5. **Almacenamiento Final**: PostgreSQL + PostGIS con tabla optimizada e índices espaciales GIST
6. **Exposición**: FastAPI con endpoints RESTful y consultas espaciales SQL (ST_DWithin, ST_ClusterDBSCAN)
7. **Visualización**: Streamlit + Folium para mapa interactivo

### Stack Tecnológico

| Componente       | Tecnología                       |
|------------------|----------------------------------|
| Orquestación     | Mage AI                          |
| Base de Datos    | PostgreSQL 16 + PostGIS 3.4      |
| Procesamiento    | Python, Pandas, GeoPandas        |
| Backend/API      | FastAPI, Uvicorn, SQLAlchemy     |
| Visualización    | Streamlit, Folium, Plotly        |
| Infraestructura  | Docker, Docker Compose           |

### Diagrama de Arquitectura

```
                     ┌─────────────────────────────────────┐
                     │       USGS Earthquake API           │
                     │       (fuente geoespacial)          │
                     └──────────────┬──────────────────────┘
                                    │ HTTP GET
                                    ▼
┌─────────────────────┐    ┌──────────────────────────────────────┐
│                     │    │  Mage AI (Orquestador)               │
│  Programa tareas    │◄───│  Pipeline: earthquake_pipeline       │
│  cada 12 horas      │    │  Bloques: extract_load → transform  │
│                     │    └──────────┬───────────────────────────┘
└─────────────────────┘               │ orquesta
                                      ▼
          ┌──────────────────────────────────────────────────┐
          │  Scripts Python (Extract & Load)                 │
          │  extract_load.py                                 │
          │  • Consulta API USGS                             │
          │  • Almacena datos crudos sin transformar         │
          └──────────────────────┬───────────────────────────┘
                                 │ INSERT raw_earthquakes
                                 ▼
          ┌──────────────────────────────────────────────────┐
          │  PostgreSQL + PostGIS (Base de Datos Espacial)   │
          │  ┌────────────────────────────────────────────┐  │
          │  │ raw_earthquakes (datos crudos)             │  │
          │  │ • Sin geometría, solo lng/lat numéricos    │  │
          │  └────────────────────────────────────────────┘  │
          └──────────────────────┬───────────────────────────┘
                                 │ SELECT (Lectura SQL)
                                 ▼
          ┌──────────────────────────────────────────────────┐
          │  Pandas / GeoPandas (Transformación Espacial)   │
          │  transform_load.py                              │
          │  • Limpieza de valores nulos                    │
          │  • Conversión lng/lat → geometrías Point        │
          │  • CRS EPSG:4326                                │
          │  • Validación de coordenadas                    │
          └──────────────────────┬───────────────────────────┘
                                 │ INSERT con geometrías
                                 ▼
          ┌──────────────────────────────────────────────────┐
          │  PostgreSQL + PostGIS (Tabla Final Optimizada)   │
          │  ┌────────────────────────────────────────────┐  │
          │  │ earthquakes                                │  │
          │  │ • location GEOGRAPHY(Point, 4326)          │  │
          │  │ • geom GEOMETRY(Point, 4326)               │  │
          │  │ • Índices GIST espaciales                  │  │
          │  └────────────────────────────────────────────┘  │
          └──────────────────────┬───────────────────────────┘
                                 │ Consultas espaciales SQL
                                 ▼
          ┌──────────────────────────────────────────────────┐
          │  FastAPI + Uvicorn (Backend / API RESTful)       │
          │  • GET  /api/v1/earthquakes                      │
          │  • GET  /api/v1/earthquakes/radius?lat&lon&dist  │
          │  • GET  /api/v1/earthquakes/stats                │
          │  • GET  /api/v1/earthquakes/clusters             │
          │  • Swagger UI en /docs                           │
          └──────────────────────┬───────────────────────────┘
                                 │ HTTP JSON
                                 ▼
          ┌──────────────────────────────────────────────────┐
          │  Streamlit + Folium (Dashboard Interactivo)      │
          │  • Mapa interactivo con círculos por magnitud    │
          │  • KPIs: total, mag promedio, tsunamis           │
          │  • Filtros: magnitud, días, búsqueda radial      │
          │  • Clusters DBSCAN                               │
          │  • Auto-refresh cada 30 segundos                 │
          └──────────────────────┬───────────────────────────┘
                                 │ Visualización
                                 ▼
                    ┌──────────────────────┐
                    │  Usuario de Negocio  │
                    └──────────────────────┘
```

### Flujo de Datos (Etapas)

| Etapa | Descripción | Componente |
|-------|-------------|------------|
| 1 | Consultar API externa | `requests.get(USGS_URL)` |
| 2 | Almacenar datos crudos | `raw_earthquakes` (PostGIS) |
| 3 | Leer datos crudos | `pd.read_sql("SELECT ...", engine)` |
| 4 | Limpiar y transformar | GeoPandas → `Point(lng, lat)` |
| 5 | Cargar tabla final | `earthquakes` con `GEOGRAPHY/GEOMETRY` |
| 6 | Exponer vía API | FastAPI con consultas espaciales |
| 7 | Visualizar | Streamlit + Folium |

### Puerto de Servicios

| Servicio    | Puerto | URL                        |
|-------------|--------|----------------------------|
| PostGIS     | 5433   | localhost:5433              |
| Mage AI DB  | 5434   | localhost:5434              |
| Mage AI     | 6789   | http://localhost:6789       |
| FastAPI     | 8000   | http://localhost:8000       |
| Swagger UI  | 8000   | http://localhost:8000/docs  |
| Streamlit   | 8501   | http://localhost:8501       |

### Estructura del Pipeline (Mage AI)

Pipeline: **earthquake_pipeline**

```
Block 1: extract_and_load (data_loader)
  ├── Tipo: Data Loader
  ├── Script: extract_load.py
  ├── Acción: Consulta USGS API → INSERT en raw_earthquakes
  └── Retry: 2 intentos, 10s de espera

Block 2: transform_and_load (data_exporter)
  ├── Tipo: Data Exporter
  ├── Script: transform_load.py
  ├── Acción: SELECT desde raw_earthquakes → GeoPandas → INSERT en earthquakes
  └── Retry: 2 intentos, 10s de espera

Trigger: Cada 12 horas (cron: 0 */12 * * *)
```

## Modelado Entidad-Relación (ERD)

### Tabla: raw_earthquakes (datos crudos)

| Columna        | Tipo              | Descripción                    |
|----------------|-------------------|--------------------------------|
| id (PK)        | VARCHAR(50)       | Identificador único            |
| usgs_id (UQ)   | VARCHAR(100)      | ID de USGS (upsert key)        |
| mag            | NUMERIC(6,2)      | Magnitud del sismo             |
| place          | TEXT              | Descripción de ubicación       |
| time           | TIMESTAMPTZ       | Fecha/hora del evento          |
| updated        | TIMESTAMPTZ       | Última actualización           |
| tz             | INTEGER           | Zona horaria                   |
| url            | TEXT              | URL del detalle                |
| felt           | INTEGER           | Reportes de personas           |
| cdi            | NUMERIC(4,2)      | Intensidad instrumental        |
| mmi            | NUMERIC(4,2)      | Intensidad mercalli            |
| alert          | VARCHAR(20)       | Nivel de alerta                |
| status         | VARCHAR(20)       | Estado del evento              |
| tsunami        | INTEGER           | 1 si generó tsunami            |
| sig            | INTEGER           | Significancia                  |
| magType        | VARCHAR(20)       | Tipo de magnitud               |
| longitude      | NUMERIC(10,6)     | Longitud (cruda)               |
| latitude       | NUMERIC(10,6)     | Latitud (cruda)                |
| depth          | NUMERIC(10,2)     | Profundidad (km)               |
| ingested_at    | TIMESTAMPTZ       | Fecha de ingesta               |

### Tabla: earthquakes (final optimizada con geometrías)

| Columna        | Tipo                    | Descripción                    |
|----------------|-------------------------|--------------------------------|
| id (PK)        | SERIAL                  | Identificador autoincremental  |
| usgs_id (UQ)   | VARCHAR(100)            | ID de USGS (upsert key)        |
| mag            | NUMERIC(6,2)            | Magnitud del sismo             |
| place          | TEXT                    | Descripción de ubicación       |
| time           | TIMESTAMPTZ             | Fecha/hora del evento          |
| updated        | TIMESTAMPTZ             | Última actualización           |
| magType        | VARCHAR(20)             | Tipo de magnitud               |
| tsunami        | INTEGER DEFAULT 0       | 1 si generó tsunami            |
| alert          | VARCHAR(20)             | Nivel de alerta                |
| status         | VARCHAR(20)             | Estado del evento              |
| sig            | INTEGER                 | Significancia                  |
| depth          | NUMERIC(10,2)           | Profundidad (km)               |
| **location**   | **GEOGRAPHY(Point, 4326)** | Ubicación geodésica         |
| **geom**       | **GEOMETRY(Point, 4326)**  | Geometría para operaciones   |
| processed_at   | TIMESTAMPTZ             | Fecha de procesamiento         |

### Índices Espaciales

| Índice                          | Tipo | Columna   | Propósito                     |
|---------------------------------|------|-----------|-------------------------------|
| `idx_earthquakes_location`      | GIST | location  | Búsqueda geodésica por radio  |
| `idx_earthquakes_geom`          | GIST | geom      | Clustering espacial (DBSCAN)  |
| `idx_earthquakes_mag`           | BTREE| mag DESC  | Filtro por magnitud           |
| `idx_earthquakes_time`          | BTREE| time DESC | Ordenamiento temporal         |
| `idx_earthquakes_tsunami`       | BTREE| tsunami   | Filtro de tsunamis            |

### Estrategia de Columnas Espaciales

| Columna   | Tipo            | SRID | Propósito                         |
|-----------|-----------------|------|-----------------------------------|
| `location`| GEOGRAPHY(Point)| 4326 | Cálculos precisos sobre el       |
|           |                 |      | elipsoide (distancias en metros)  |
| `geom`    | GEOMETRY(Point) | 4326 | Operaciones geométricas           |
|           |                 |      | (clusters, bounding boxes)        |

### Consultas Espaciales Implementadas

1. **Búsqueda radial** (`ST_DWithin`): Encuentra sismos en un radio (metros)
2. **Clustering** (`ST_ClusterDBSCAN`): Agrupa sismos por densidad espacial
3. **Distancias** (`ST_Distance`): Calcula distancia geodésica precisa
4. **Proyección** (`ST_X/ST_Y`): Extrae coordenadas de geometrías

### Funciones Almacenadas

- `get_earthquake_clusters(radius_km)`: Clusters DBSCAN de última semana
- `get_earthquake_summary()`: Estadísticas agregadas del dataset

## Estrategia de Normalización

- **raw_earthquakes**: Tabla plana sin normalizar. Almacena todos los campos
  tal cual llegan de la API. Sin geometrías PostGIS.
- **earthquakes**: Tabla optimizada con columnas espaciales (GEOGRAPHY y
  GEOMETRY). Contiene solo los campos relevantes para consultas analíticas
  y geoespaciales.
- Las coordenadas se almacenan como POINT con SRID 4326 (WGS84).
- La separación raw/final permite reprocesar datos sin pérdida de
  información original.
