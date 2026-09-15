import os
import sqlite3

from undercurrents.storage import db

DB_PATH = os.environ.get("UNDERCURRENTS_DB_PATH", "data/undercurrents.db")


def get_conn():
    # check_same_thread=False: FastAPI's threadpool may enter this generator dependency
    # (contextmanager_in_threadpool.__enter__) on one worker thread and run the endpoint body
    # (a separate run_in_threadpool call) on another -- sqlite3's default thread affinity check
    # then rejects the connection even though it's only ever used sequentially within one
    # request, never concurrently across requests (a fresh connection is opened and closed per
    # request). db.get_connection() keeps the strict default for its other, genuinely
    # single-threaded callers (CLI tools, tests).
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    db.ensure_songs_clustering_columns(conn)
    try:
        yield conn
    finally:
        conn.close()
