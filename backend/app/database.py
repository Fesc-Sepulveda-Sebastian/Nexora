import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup (PostgreSQL / SQLite fallback)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# MongoDB Client setup with graceful fallback for local development
mongo_client = None
mongo_db = None

try:
    from pymongo import MongoClient
    mongo_client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
    # Ping mongo to check connectivity
    mongo_client.admin.command('ping')
    mongo_db = mongo_client[settings.MONGODB_DB_NAME]
    logger.info("MongoDB connection established successfully.")
except Exception as e:
    logger.warning(f"MongoDB not available ({e}). Using in-memory / JSON fallback store for metric snapshots.")
    mongo_db = None

def get_mongo_db():
    return mongo_db

def init_db():
    # Import all models to register with Base
    import app.models # noqa
    Base.metadata.create_all(bind=engine)
    if settings.DATABASE_URL.startswith("sqlite"):
        _ensure_sqlite_profile_columns()
    logger.info("SQL database tables initialized successfully.")


def _ensure_sqlite_profile_columns():
    new_columns = {
        "has_infractions": "BOOLEAN DEFAULT 0",
        "is_available": "BOOLEAN DEFAULT 1",
        "is_verified": "BOOLEAN DEFAULT 1",
        "has_debts": "BOOLEAN DEFAULT 0",
        "followers_declared": "INTEGER DEFAULT 0",
    }
    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(profiles)")).fetchall()}
        for col_name, col_def in new_columns.items():
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE profiles ADD COLUMN {col_name} {col_def}"))
