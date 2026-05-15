from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.routers import earthquakes

app = FastAPI(
    title="Earthquakes API - Datos Geoespaciales",
    description="API RESTful para consulta de datos sísmicos con PostGIS",
    version="1.0.0",
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(earthquakes.router)
