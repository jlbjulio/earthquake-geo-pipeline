# Proyecto Semestral - Arquitectura y Exposicion de Datos Geoespaciales

**Integrantes:**
- Julio Lara - 8-997-2325
- Joseph Batista - 8-1009-1500

Pipeline end-to-end de datos geoespaciales con orquestacion en Mage AI, almacenamiento PostGIS, backend FastAPI y dashboard Streamlit.

## Stack

| Componente      | Tecnologia                  |
| --------------- | --------------------------- |
| Orquestacion    | Mage AI                     |
| Base de Datos   | PostgreSQL 16 + PostGIS 3.4 |
| Procesamiento   | Python, Pandas, GeoPandas   |
| Backend / API   | FastAPI, Uvicorn, SQLAlchemy |
| Visualizacion   | Streamlit, Folium           |
| Infraestructura | Docker, Docker Compose      |

## Arquitectura

```text
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
  FastAPI + Uvicorn  (endpoints REST + Swagger)
        |
        | HTTP JSON
        v
  Streamlit + Folium  (dashboard con mapa interactivo)
        |
        v
  Usuario
        ^
        |
  Mage AI  (orquesta pipeline cada 12h)
```

## Mejoras de rendimiento y presentacion

- La carga cruda usa inserciones por lote en vez de insertar evento por evento.
- La transformacion ahora es incremental: solo procesa eventos nuevos o eventos cuyo `updated` cambio en USGS.
- Se agregaron indices para filtros frecuentes: tiempo, magnitud y actualizacion.
- El dashboard limita la cantidad dibujada en mapa/tabla para mantener respuesta fluida sin borrar datos de la base.
- El resumen visual se reorganizo con tarjetas analiticas, graficas claras y eventos destacados.
- La paleta visual se normalizo: fondos claros para texto chocolate y barra lateral chocolate con texto claro.

## Servicios

| Servicio   | Puerto | URL                        |
| ---------- | ------ | -------------------------- |
| PostGIS    | 5433   | localhost:5433             |
| Mage AI    | 6789   | http://localhost:6789      |
| FastAPI    | 8001   | http://localhost:8001      |
| Swagger UI | 8001   | http://localhost:8001/docs |
| Streamlit  | 8501   | http://localhost:8501      |

El backend se publica en `8001` para evitar conflictos con otros proyectos FastAPI que suelen usar `8000`. Dentro de Docker, los servicios siguen comunicandose con el backend por `http://backend:8000`.

## Estructura del Proyecto

```text
.
+-- docker-compose.yml
+-- postgres/init/01_init.sql
+-- scripts/
|   +-- extract_load.py
|   +-- transform_load.py
+-- mage_project/
|   +-- pipelines/earthquake_pipeline/
|   |   +-- blocks/
|   |   +-- triggers.yaml
+-- backend/
|   +-- app/
|       +-- main.py
|       +-- models.py
|       +-- routers/earthquakes.py
+-- dashboard/
|   +-- app.py
+-- docs/
|   +-- architecture.md
|   +-- erd.md
|   +-- diagrama_arquitectura.drawio
+-- presentacion_final.md
```

## Endpoints de la API

| Metodo | Endpoint                        | Descripcion                            |
| ------ | ------------------------------- | -------------------------------------- |
| GET    | `/api/v1/health`                | Healthcheck del backend                |
| GET    | `/api/v1/earthquakes`           | Lista con filtros de magnitud y tiempo |
| GET    | `/api/v1/earthquakes/radius`    | Busqueda radial con `ST_DWithin`       |
| GET    | `/api/v1/earthquakes/stats`     | Estadisticas via funcion SQL           |
| GET    | `/api/v1/earthquakes/analysis`  | Analisis agregado para el dashboard    |
| GET    | `/api/v1/earthquakes/clusters`  | Clusters espaciales con DBSCAN         |
| GET    | `/api/v1/earthquakes/{usgs_id}` | Detalle por ID de USGS                 |

## Uso

```bash
docker compose up -d --build
```

Luego abrir:

- Dashboard: http://localhost:8501
- API Docs: http://localhost:8001/docs
- Mage AI: http://localhost:6789

Para ejecutar el pipeline manualmente desde consola:

```bash
docker compose exec -w /home/src/earthquake_geo_pipeline mage python scripts/extract_load.py
docker compose exec -w /home/src/earthquake_geo_pipeline mage python scripts/transform_load.py
```

Tambien se puede ejecutar desde la UI de Mage AI abriendo el pipeline `earthquake_pipeline`. El trigger incluido queda configurado para correr cada 12 horas.

## Variables de entorno principales

Copiar `.env.example` a `.env` si hace falta personalizar puertos o credenciales.

```env
POSTGIS_PORT=5433
BACKEND_PORT=8001
MAGE_PORT=6789
DASHBOARD_PORT=8501
API_PUBLIC_URL=http://localhost:8001
USGS_FEED_URL=https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson
```

## Datos

Fuente: [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php). Es una API publica en formato GeoJSON, actualizada continuamente y sin autenticacion.
