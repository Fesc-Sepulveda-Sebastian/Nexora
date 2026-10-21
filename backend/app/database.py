import logging
from sqlalchemy import create_engine
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
    logger.info("SQL database tables initialized successfully.")
