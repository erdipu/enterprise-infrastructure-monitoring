import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import settings

logger = logging.getLogger("monitoring.database")

Base = declarative_base()

# Attempt PostgreSQL connection, fall back gracefully to local SQLite if PostgreSQL is unavailable
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={"connect_timeout": 3} if settings.DATABASE_URL.startswith("postgresql") else {}
    )
    # Quick connectivity test
    with engine.connect() as conn:
        logger.info("Connected to PostgreSQL database successfully.")
except Exception as e:
    logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite engine: {settings.SQLITE_FALLBACK_URL}")
    engine = create_engine(
        settings.SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
