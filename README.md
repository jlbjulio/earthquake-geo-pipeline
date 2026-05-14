# Proyecto Semestral — Arquitectura y Exposición de Datos Geoespaciales

Pipeline end-to-end de datos geoespaciales con orquestación en Mage AI, almacenamiento PostGIS, backend FastAPI y dashboard Streamlit.

## Stack

| Componente      | Tecnología                   |
| --------------- | ---------------------------- |
| Orquestacion    | Mage AI                      |
| Base de Datos   | PostgreSQL 16 + PostGIS 3.4  |
| Procesamiento   | Python, Pandas, GeoPandas    |
| Backend / API   | FastAPI, Uvicorn, SQLAlchemy |
| Visualizacion   | Streamlit, Folium            |
| Infraestructura | Docker, Docker Compose       |

## Arquitectura

```
USGS Earthquake API
        |
        v
  [Extract & Load]  scripts/extract_load.py
        |
        | raw_earthquakes
        v
  PostgreSQL + PostGIS
        |
        | lectura SQL
        v
  [Transform]  scripts/transform_load.py  (GeoPandas)
        |
        | geometrias Point
        v
  PostgreSQL + PostGIS  (tabla final con indices GIST)
        |
        | consultas espaciales SQL
        v
  FastAPI + Uvicorn  (5 endpoints REST + Swagger)
        |
        | HTTP JSON
        v
  Streamlit + Folium  (dashboard con mapa interactivo)
        |
        v
  Usuario de Negocio
        ^
        |
  Mage AI  (orquesta pipeline cada 12h)
```

## Servicios

| Servicio   | Puerto | URL                        |
| ---------- | ------ | -------------------------- |
| PostGIS    | 5433   | localhost:5433             |
| Mage AI    | 6789   | http://localhost:6789      |
| FastAPI    | 8000   | http://localhost:8000      |
| Swagger UI | 8000   | http://localhost:8000/docs |
| Streamlit  | 8501   | http://localhost:8501      |

## Estructura del Proyecto

```
.
+-- docker-compose.yml
+-- postgres/init/01_init.sql          DDL con PostGIS
+-- scripts/
|   +-- extract_load.py               Extrae API y carga raw a PostGIS
|   +-- transform_load.py             Lee raw, transforma con GeoPandas, carga final
+-- mage_project/
|   +-- pipelines/earthquake_pipeline/ Pipeline de Mage AI
|   |   +-- blocks/                   extract_load + transform_load
|   |   +-- triggers/schedule_12h.yaml  Trigger cada 12 horas
+-- backend/
|   +-- app/
|       +-- main.py                   FastAPI entrypoint
|       +-- models.py                 Modelo SQLAlchemy con Geography/Geometry
|       +-- routers/earthquakes.py    5 endpoints espaciales
+-- dashboard/
|   +-- app.py                        Streamlit + Folium
+-- docs/
|   +-- architecture.md               Especificacion tecnica
|   +-- diagrama_arquitectura.drawio   Diagrama en Draw.io
+-- presentacion_final.md
```

## Endpoints de la API

| Metodo | Endpoint                        | Descripcion                            |
| ------ | ------------------------------- | -------------------------------------- |
| GET    | `/api/v1/earthquakes`           | Lista con filtros (magnitud, tiempo)   |
| GET    | `/api/v1/earthquakes/radius`    | Busqueda radial con ST_DWithin         |
| GET    | `/api/v1/earthquakes/stats`     | Estadisticas via funcion SQL           |
| GET    | `/api/v1/earthquakes/clusters`  | Clusters espaciales (ST_ClusterDBSCAN) |
| GET    | `/api/v1/earthquakes/{usgs_id}` | Detalle por ID                         |

## Uso

```bash
docker-compose up -d
```

Luego abrir:

- Dashboard: http://localhost:8501
- API Docs: http://localhost:8000/docs
- Mage AI: http://localhost:6789

El pipeline se ejecuta automaticamente cada 12 horas. Tambien se puede ejecutar manualmente desde la UI de Mage AI.

## Datos

Fuente: [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) — API publica sin autenticacion, formato GeoJSON, actualizada en tiempo real.
