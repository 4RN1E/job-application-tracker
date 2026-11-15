"""Database connection helpers.

Connection settings come from environment variables (or a local .env file),
so no password is ever committed to GitHub. Copy .env.example to .env and
fill in your own values.
"""
import json
import os
from contextlib import contextmanager

import mysql.connector

try:  # python-dotenv is optional: without it, use real environment variables
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def db_config():
    """Read connection settings at call time so tests can override them."""
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ.get("DB_USER", "root"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "database": os.environ.get("DB_NAME", "job_tracker"),
    }


def get_db():
    """Open a new MySQL connection."""
    return mysql.connector.connect(**db_config())


@contextmanager
def db_cursor(commit=False):
    """Yield a dict cursor; always close the connection afterwards.

    Pass commit=True for INSERT / UPDATE / DELETE so the change is saved.
    On any error the transaction is rolled back.
    """
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def fetch_all(sql, params=()):
    """Run a SELECT and return every row as a dict."""
    with db_cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def fetch_one(sql, params=()):
    """Run a SELECT and return the first row (or None)."""
    with db_cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def execute(sql, params=()):
    """Run an INSERT / UPDATE / DELETE. Returns the new row id for inserts."""
    with db_cursor(commit=True) as cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid


def load_json(value, default=None):
    """Turn a JSON column value into a Python object.

    Depending on the server and connector version a JSON column can come back
    as str, bytes, or already-parsed data, so handle all of them.
    """
    if value is None:
        return default
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return default
    return value
