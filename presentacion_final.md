# Presentacion Final: Proyecto Semestral

## Arquitectura y Exposicion de Datos Geoespaciales

### Datos del Proyecto

- **Curso:** Topicos Especiales II
- **Integrantes:** Julio Lara (8-997-2325), Joseph Batista (8-1009-1500)
- **Stack:** Mage AI, PostgreSQL/PostGIS, Python/GeoPandas, FastAPI, Streamlit, Docker
- **Fuente:** USGS Earthquake Catalog, API publica GeoJSON en tiempo real

---

## Flujo Completo E2E

```text
1. USGS Earthquake API
       |
2. Mage AI ejecuta earthquake_pipeline
       |
3. Extract & Load: scripts/extract_load.py
       |
4. PostGIS: raw_earthquakes
       |
5. Transform & Load: scripts/transform_load.py
       |
6. PostGIS: earthquakes con GEOGRAPHY, GEOMETRY e indices GIST
       |
7. FastAPI: endpoints REST /api/v1/*
       |
8. Streamlit + Folium: dashboard interactivo
```

---

## Demostracion

### 1. Levantar infraestructura

```bash
docker compose up -d --build
```

Servicios levantados:

| Servicio | URL |
| -------- | --- |
| Dashboard | http://localhost:8501 |
| API Docs | http://localhost:8001/docs |
| Mage AI | http://localhost:6789 |
| PostGIS | localhost:5433 |

El API se publica en `8001` para no chocar con otros proyectos FastAPI que usen `8000`.

### 2. Ejecutar pipeline

Desde Mage AI:

- Abrir http://localhost:6789
- Entrar al pipeline `earthquake_pipeline`
- Ejecutar los bloques `extract_and_load` y `transform_and_load`

Desde consola:

```bash
docker compose exec -w /home/src mage mage run earthquake_geo_pipeline earthquake_pipeline
```

### 3. Verificar datos

```bash
curl http://localhost:8001/api/v1/earthquakes/stats
curl "http://localhost:8001/api/v1/earthquakes?limit=5&days_back=30"
```

---

## Componentes

### Mage AI

- Orquesta el pipeline `earthquake_pipeline`.
- Tiene un trigger configurado cada 12 horas.
- Ejecuta dos bloques principales:
  - `extract_and_load`
  - `transform_and_load`

### PostGIS

- `raw_earthquakes`: tabla cruda con datos de USGS.
- `earthquakes`: tabla final con columnas espaciales.
- Indices GIST para consultas rapidas.
- Funciones SQL para resumen y consultas espaciales.

### FastAPI

Endpoints principales:

| Endpoint | Funcion |
| -------- | ------- |
| `/api/v1/health` | Healthcheck |
| `/api/v1/earthquakes` | Lista de sismos con filtros |
| `/api/v1/earthquakes/radius` | Busqueda radial con `ST_DWithin` |
| `/api/v1/earthquakes/stats` | KPIs |
| `/api/v1/earthquakes/clusters` | Clusters DBSCAN |

### Streamlit

- KPIs: total de eventos, magnitud promedio, magnitud maxima y tsunamis.
- Mapa Folium con marcadores por magnitud.
- Filtros por magnitud, dias y radio geografico.
- Tabla de ultimos eventos.
- Resumen visual por categoria de magnitud y eventos recientes.

---

## Funcionalidades Espaciales

| Funcionalidad | Tecnologia |
| ------------- | ---------- |
| Puntos geograficos | PostGIS `GEOGRAPHY(Point, 4326)` |
| Indices espaciales | GIST |
| Busqueda por radio | `ST_DWithin` |
| Calculo de distancia | `ST_Distance` |
| Clustering | `ST_ClusterDBSCAN` |
| Visualizacion | Folium sobre Streamlit |

---

## Resultado Final

- Pipeline reproducible con Docker Compose.
- Mage AI funcionando para orquestacion.
- Datos cargados en PostGIS.
- API documentada con Swagger.
- Dashboard interactivo listo para presentacion.
- Puertos configurados para convivir con otros contenedores locales.
