import pytest

from undercurrents.storage import db


@pytest.fixture
def tmp_conn():
    conn = db.get_connection(":memory:")
    db.initialize_schema(conn)
    yield conn
    conn.close()
