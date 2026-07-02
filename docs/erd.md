# ERD - Modelo Entidad-Relacion

Este modelo separa los datos crudos de USGS de la tabla final optimizada para consultas espaciales.

```mermaid
erDiagram
    RAW_EARTHQUAKES {
        varchar id PK
        varchar usgs_id UK
        numeric mag
        text place
        timestamptz time
        timestamptz updated
        text url
        integer tsunami
        integer sig
        varchar magType
        numeric longitude
        numeric latitude
        numeric depth
        timestamptz ingested_at
    }

    EARTHQUAKES {
        serial id PK
        varchar usgs_id UK
        numeric mag
        text place
        timestamptz time
        timestamptz updated
        varchar magType
        integer tsunami
        varchar alert
        varchar status
        integer sig
        numeric depth
        geography location
        geometry geom
        timestamptz processed_at
    }

    RAW_EARTHQUAKES ||--o| EARTHQUAKES : "usgs_id"
```

## Estrategia

| Tabla | Proposito |
| ----- | --------- |
| `raw_earthquakes` | Conserva la respuesta de USGS con coordenadas numericas y metadatos completos. |
| `earthquakes` | Tabla final con `GEOGRAPHY(Point, 4326)` y `GEOMETRY(Point, 4326)` para consultas espaciales. |

## Normalizacion

- Se mantiene una tabla raw para preservar la fuente original.
- La tabla final contiene los campos necesarios para API, dashboard y analisis geoespacial.
- `usgs_id` es la clave logica para upserts y evita duplicados.
- `location` se usa para distancias precisas en metros.
- `geom` se usa para indices GIST y operaciones geometricas.
