from geoalchemy2 import Geography, Geometry
from sqlalchemy import Column, Integer, Numeric, String, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Earthquake(Base):
    __tablename__ = "earthquakes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usgs_id = Column(String(100), unique=True, nullable=False)
    mag = Column(Numeric(6, 2))
    place = Column(Text)
    time = Column(DateTime(timezone=True))
    updated = Column(DateTime(timezone=True))
    magType = Column(String(20))
    tsunami = Column(Integer, default=0)
    alert = Column(String(20))
    status = Column(String(20))
    sig = Column(Integer)
    depth = Column(Numeric(10, 2))
    location = Column(Geography(geometry_type="Point", srid=4326))
    geom = Column(Geometry(geometry_type="Point", srid=4326))
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
