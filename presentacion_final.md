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
docker compose exec -w /home/src/earthquake_geo_pipeline mage python scripts/extract_load.py
docker compose exec -w /home/src/earthquake_geo_pipeline mage python scripts/transform_load.py
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
- La transformacion es incremental: solo reprocesa eventos nuevos o actualizados.

### PostGIS

- `raw_earthquakes`: tabla cruda con datos de USGS.
- `earthquakes`: tabla final con columnas espaciales.
- Indices GIST para consultas rapidas.
- Indices adicionales por tiempo, magnitud y actualizacion para acelerar filtros.
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

- KPIs: total de eventos, eventos visibles, magnitud maxima y profundidad promedio.
- Mapa Folium con marcadores por magnitud.
- Filtros por magnitud, dias y radio geografico.
- Tabla de eventos con paleta clara y scroll.
- Resumen visual con tarjetas analiticas, distribucion por magnitud, zonas frecuentes y magnitud vs profundidad.

---

## Mejoras Implementadas Tras el Avance

### Rendimiento de datos

- Antes el proceso podia volver a transformar todos los registros crudos.
- Ahora el ETL usa carga por lote e identifica registros nuevos o actualizados.
- En la ultima validacion, despues de extraer la fuente mensual, solo se transformaron 4 registros incrementales.
- Esto reduce trabajo innecesario y hace mas estable la ejecucion cada 12 horas.

### Visualizacion

- Se corrigio la paleta para evitar texto oscuro sobre fondos oscuros.
- Se redisenaron tabla, graficas, encabezado, dropdowns y barra lateral.
- El dashboard mantiene limites de dibujo para que el mapa no cargue demasiados puntos al mismo tiempo.

### Analisis

- Se agregaron tarjetas interpretativas.
- Las graficas ahora explican distribucion por magnitud, zonas mas frecuentes y relacion magnitud/profundidad.
- Los eventos destacados permiten identificar rapidamente los sismos mas importantes.

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
