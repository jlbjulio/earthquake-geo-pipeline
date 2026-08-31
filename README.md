# Earthquake Geospatial Data Pipeline

An end-to-end data platform for collecting, processing, storing, exposing, and visualizing global earthquake data from the United States Geological Survey (USGS).

The system combines automated orchestration, spatial data processing, a REST API, and an interactive dashboard in a fully containerized environment.

## Overview

Earthquake events are retrieved from the USGS GeoJSON feed and loaded into PostgreSQL. GeoPandas transforms the raw records into spatial features, which are stored in PostGIS and optimized for geospatial queries. FastAPI exposes the processed data through REST endpoints, while Streamlit and Folium provide an interactive analytical dashboard.

Mage AI orchestrates the pipeline automatically every 12 hours.

## Key Features

- Automated ingestion from the USGS Earthquake API.
- Batch inserts for efficient raw-data loading.
- Incremental processing of new and updated events.
- Native geospatial storage with PostgreSQL and PostGIS.
- GIST indexes for optimized spatial queries.
- Radius-based earthquake searches using `ST_DWithin`.
- Spatial clustering with DBSCAN.
- REST API with interactive Swagger documentation.
- Interactive maps, analytical summaries, and event highlights.
- Fully containerized setup with Docker Compose.
- Scheduled pipeline execution with Mage AI.

## Technology Stack

| Component | Technology |
| --- | --- |
| Orchestration | Mage AI |
| Database | PostgreSQL 16 and PostGIS 3.4 |
| Data Processing | Python, Pandas, and GeoPandas |
| Backend API | FastAPI, Uvicorn, and SQLAlchemy |
| Visualization | Streamlit and Folium |
| Infrastructure | Docker and Docker Compose |

## Architecture

```text
USGS Earthquake API
        |
        v
  Extract and Load
  scripts/extract_load.py
        |
        | raw_earthquakes
        v
  PostgreSQL + PostGIS
        |
        | SQL read
        v
  Transform
  scripts/transform_load.py (GeoPandas)
        |
        | Point geometries
        v
  PostgreSQL + PostGIS
  Final table with GIST indexes
        |
        | Spatial SQL queries
        v
  FastAPI + Uvicorn
  REST endpoints and Swagger UI
        |
        | HTTP / JSON
        v
  Streamlit + Folium
  Interactive analytics dashboard
        |
        v
      User
        ^
        |
  Mage AI orchestrates the pipeline every 12 hours
```

## Repository Structure

```text
.
+-- docker-compose.yml
+-- postgres/
|   +-- init/
|       +-- 01_init.sql
+-- scripts/
|   +-- extract_load.py
|   +-- transform_load.py
+-- mage_project/
|   +-- pipelines/
|       +-- earthquake_pipeline/
|           +-- blocks/
|           +-- triggers.yaml
+-- backend/
|   +-- app/
|       +-- main.py
|       +-- models.py
|       +-- routers/
|           +-- earthquakes.py
+-- dashboard/
|   +-- app.py
+-- docs/
|   +-- architecture.md
|   +-- erd.md
|   +-- diagrama_arquitectura.drawio
+-- presentacion_final.md
```

## Getting Started

### Prerequisites

- Git
- Docker Desktop on Windows or macOS, or Docker Engine with Compose on Linux
- At least 4 GB of memory available to Docker

On ARM64 systems such as Apple Silicon, Docker Desktop runs the PostGIS image through AMD64 emulation. The initial build may therefore take longer. Linux ARM64 environments require Docker's `binfmt/qemu` emulation to be enabled.

### Installation

Clone the repository using its GitHub URL and enter the directory:

```bash
git clone <repository-url>
cd earthquake-geo-pipeline
```

The repository includes a local `.env` configuration. Update it before starting the services if different ports or credentials are required.

Build and start the complete stack:

```bash
docker compose up -d --build
```

Confirm that every service has reached the `healthy` state:

```bash
docker compose ps
```

## Services

| Service | Port | URL |
| --- | ---: | --- |
| PostGIS | 5433 | `localhost:5433` |
| Mage AI | 6789 | http://localhost:6789 |
| FastAPI | 8001 | http://localhost:8001 |
| Swagger UI | 8001 | http://localhost:8001/docs |
| Streamlit | 8501 | http://localhost:8501 |

The backend is exposed on port `8001` to avoid conflicts with applications commonly using port `8000`. Inside the Docker network, services communicate with the backend through `http://backend:8000`.

## API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Check the backend health status |
| `GET` | `/api/v1/earthquakes` | List events with magnitude and time filters |
| `GET` | `/api/v1/earthquakes/radius` | Search for events within a geographic radius |
| `GET` | `/api/v1/earthquakes/stats` | Retrieve aggregated statistics from SQL |
| `GET` | `/api/v1/earthquakes/analysis` | Retrieve aggregated dashboard analytics |
| `GET` | `/api/v1/earthquakes/clusters` | Retrieve DBSCAN spatial clusters |
| `GET` | `/api/v1/earthquakes/{usgs_id}` | Retrieve an event by its USGS identifier |

Interactive API documentation is available at http://localhost:8001/docs after the services start.

## Running the Pipeline

Run the extraction and transformation stages manually:

```bash
docker compose exec -w /home/src/earthquake_geo_pipeline mage python scripts/extract_load.py
docker compose exec -w /home/src/earthquake_geo_pipeline mage python scripts/transform_load.py
```

The pipeline can also be started from the Mage AI interface by opening `earthquake_pipeline`.

The included trigger runs every 12 hours. On a new installation, Mage registers the trigger from `mage_project/pipelines/earthquake_pipeline/triggers.yaml` and automatically creates the first execution, allowing the dashboard to receive data without waiting for the next scheduled interval.

## Configuration

The main configuration values are defined in `.env`. The `.env.example` file documents the available options.

```env
POSTGIS_PORT=5433
BACKEND_PORT=8001
MAGE_PORT=6789
DASHBOARD_PORT=8501
API_PUBLIC_URL=http://localhost:8001
USGS_FEED_URL=https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson
```

## Updating

Pull the latest changes and rebuild the services:

```bash
git pull
docker compose up -d --build
```

Existing PostgreSQL and Mage volumes are preserved during this process.

## Troubleshooting

Check the service status and recent logs:

```bash
docker compose ps
docker compose logs --tail=100 mage
docker compose logs --tail=100 backend
docker compose logs --tail=100 dashboard
```

If the scheduled trigger does not appear after an update, restart Mage:

```bash
docker compose restart mage
```

> [!WARNING]
> Running `docker compose down -v` permanently removes the spatial database, users, and local Mage history.

To intentionally create a clean installation:

```bash
docker compose down -v
docker compose up -d --build
```

## Data Source

Earthquake data is provided by the [USGS Earthquake Catalog](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php), a continuously updated public GeoJSON API that does not require authentication.
