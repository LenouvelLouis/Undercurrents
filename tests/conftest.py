import sqlite3

import pytest

from undercurrents.storage import db


@pytest.fixture
def tmp_conn():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    db.initialize_schema(conn)
    yield conn
    conn.close()
