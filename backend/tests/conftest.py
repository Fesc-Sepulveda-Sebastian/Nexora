import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

# Configure an isolated temporary SQLite database and local storage dir before importing app modules
_tmp_dir = tempfile.mkdtemp(prefix="nexora_test_")
_test_db_path = os.path.join(_tmp_dir, "test_nexora.db")
_test_uploads_dir = os.path.join(_tmp_dir, "uploads")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["LOCAL_STORAGE_DIR"] = _test_uploads_dir

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.metrics_service import _fallback_snapshots_store  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    _fallback_snapshots_store.clear()
    if os.path.exists(_test_uploads_dir):
        shutil.rmtree(_test_uploads_dir, ignore_errors=True)
    yield


@pytest.fixture()
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
