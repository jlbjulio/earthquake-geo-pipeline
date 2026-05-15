# Presentación Final: Proyecto Semestral

## Arquitectura y Exposición de Datos Geoespaciales

### Datos del Proyecto
- **Curso**: Tópicos Especiales II
- **Integrantes**: Julio Lara (8-997-2325), Joseph Batista (8-1009-1500)
- **Stack**: Mage AI, PostgreSQL/PostGIS, Python/GeoPandas, FastAPI, Streamlit, Docker
- **Fuente de Datos**: USGS Earthquake Catalog (API pública, GeoJSON en tiempo real)

---

## Flujo Completo E2E

```
1. USGS Earthquake API (fuente externa)
         ↓ HTTP GET
2. Mage AI programa tareas cada 12h
         ↓ Ejecuta pipeline
3. Extract & Load (extract_load.py)
         ↓ Consulta API y escribe en PostgreSQL
4. raw_earthquakes (datos crudos en PostGIS)
         ↓ Lectura SQL
5. Transform & Load (transform_load.py con GeoPandas)
         ↓ Limpia, crea geometrías Point, escribe tabla final
6. earthquakes (tabla optimizada con índices GIST en PostGIS)
         ↓ Consultas espaciales SQL
7. FastAPI (endpoints RESTful /api/v1/earthquakes/*)
         ↓ HTTP JSON
8. Streamlit + Folium (dashboard interactivo con mapa)
         ↓ Visualización
9. Usuario de negocio
```

---

## Demostración del Flujo Completo

### 1. Inicio de Infraestructura
```bash
docker-compose up -d
```
Se levantan 5 contenedores: PostGIS, Mage DB, Mage AI, FastAPI, Streamlit.

### 2. Orquestación (Mage AI)
- Pipeline `earthquake_pipeline` ejecuta cada 12h automáticamente
- Trigger configurado en `triggers/schedule_12h.yaml`
- Se puede ejecutar manualmente desde la UI de Mage en http://localhost:6789

### 3. Extracción y Carga (Extract & Load)
- Script `scripts/extract_load.py` consulta la API de USGS
- Obtiene ~100-500 eventos sísmicos recientes
- Almacena datos crudos en tabla `raw_earthquakes` (upsert por usgs_id)

### 4. Transformación Espacial (Transform & Load)
- Script `scripts/transform_load.py` lee de `raw_earthquakes`
- GeoPandas convierte coordenadas (lng, lat) a geometrías `Point` (EPSG:4326)
- Limpia valores nulos, filtra coordenadas inválidas
- Carga en tabla `earthquakes` con columnas espaciales:
  - `location GEOGRAPHY(Point, 4326)` → cálculos geodésicos
  - `geom GEOMETRY(Point, 4326)` → operaciones geométricas

### 5. Consulta desde FastAPI
- `GET /api/v1/earthquakes` → Lista con filtros (magnitud, tiempo)
- `GET /api/v1/earthquakes/radius?lat=...&lon=...&dist_km=...` → Búsqueda radial con `ST_DWithin`
- `GET /api/v1/earthquakes/stats` → Estadísticas con funciones SQL
- `GET /api/v1/earthquakes/clusters` → Clusters DBSCAN con `ST_ClusterDBSCAN`
- Documentación interactiva en http://localhost:8000/docs (Swagger)

### 6. Dashboard en Streamlit
- http://localhost:8501
- KPIs: total eventos, magnitud promedio/máxima, tsunamis
- Mapa Folium interactivo con círculos coloreados por magnitud
- Filtros: magnitud mínima, días, búsqueda radial
- Clusters sísmicos DBSCAN
- Auto-refresh cada 30 segundos

---

## Funcionalidades Espaciales Implementadas

| Funcionalidad | Tecnología | Consulta SQL |
|---|---|---|
| Almacenamiento de geometrías | PostGIS `GEOGRAPHY(Point, 4326)` | `ST_GeomFromText()` |
| Índices espaciales | PostGIS GIST | `CREATE INDEX ... USING GIST` |
| Búsqueda por radio | FastAPI + PostGIS | `ST_DWithin(location, target, radius)` |
| Cálculo de distancias | FastAPI + PostGIS | `ST_Distance(location::geography, target)` |
| Clustering espacial | FastAPI + PostGIS | `ST_ClusterDBSCAN(geom, eps, minpoints)` |
| Visualización en mapa | Streamlit + Folium | `folium.CircleMarker()` |

---

## Resultados Esperados

1. **Datos actualizados cada 12h** automáticamente por Mage AI
2. **API documentada** con Swagger en `/docs`
3. **Dashboard interactivo** con mapa en tiempo real
4. **Consultas espaciales** funcionales (radio, clusters, estadísticas)
5. **Infraestructura reproducible** con Docker Compose

---

## Capturas de Pantalla (simuladas)

```
┌─────────────────────────────────────────────────────────┐
│  Dashboard de Monitoreo Sismico                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                    │
│  │Total │ │ Mag  │ │ Mag  │ │Tsuna-│                    │
│  │Eventos│ │Prom. │ │ Máx. │ │ mis  │                    │
│  │ 127   │ │ 2.4  │ │ 6.8  │ │  3   │                    │
│  └──────┘ └──────┘ └──────┘ └──────┘                    │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Mapa Mundial con eventos sismicos              │   │
│  │  ● Magnitud < 2 (verde)                           │   │
│  │  ● Magnitud 2-4 (amarillo)                        │   │
│  │  ● Magnitud 4-6 (naranja)                         │   │
│  │  ● Magnitud > 6 (rojo)                            │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌─────┬──────────────┬──────────────────┬──────┐       │
│  │ Mag │    Place     │       Time       │Depth │       │
│  ├─────┼──────────────┼──────────────────┼──────┤       │
│  │ 6.8 │ 12km S of... │2025-01-15 03:22  │ 10.0 │       │
│  │ 4.2 │ 45km E of... │2025-01-15 02:15  │ 35.2 │       │
│  └─────┴──────────────┴──────────────────┴──────┘       │
└─────────────────────────────────────────────────────────┘
```

---

## Enlaces

| Servicio | URL |
|---|---|
| Dashboard (Streamlit) | http://localhost:8501 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Mage AI | http://localhost:6789 |
| FastAPI | http://localhost:8000 |

---

## Conclusiones

- Se implementó un pipeline E2E completo de datos geoespaciales
- La arquitectura sigue el diagrama propuesto: API → Extract&Load → PostGIS → GeoPandas → PostGIS → FastAPI → Streamlit
- PostGIS permite consultas espaciales avanzadas (radio, clustering)
- Mage AI orquesta la ejecución automática cada 12 horas
- El stack es 100% reproducible mediante Docker Compose
