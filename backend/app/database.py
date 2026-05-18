import os
from sqlalchemy.engine.create import create_engine
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.orm.decl_api import declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://geo_user:geo_pass@localhost:5433/geodata"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
