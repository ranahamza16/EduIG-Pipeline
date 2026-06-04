import sqlite3
from typing import Any


def dict_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert SQLite rows into Python dictionaries."""
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


def get_db_connection(db_path: str = "data/eduig.db") -> sqlite3.Connection:
    """Get a database connection configured to return dictionaries."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    return conn
