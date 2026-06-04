import os
import pytest
from src.storage import init_db

@pytest.fixture(autouse=True, scope="session")
def enforce_memory_db():
    """Enforce :memory: database for all tests to prevent polluting local DB."""
    os.environ["EDUIG_DB_PATH"] = ":memory:"
    init_db(":memory:")
