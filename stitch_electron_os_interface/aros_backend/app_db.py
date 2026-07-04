import os
import sqlite3
import datetime

APP_DB_PATH = os.path.join(os.path.dirname(__file__), "aros_app.db")


def _connect():
    conn = sqlite3.connect(APP_DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _connect()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS category_assignments (
            barcode TEXT PRIMARY KEY,
            category_name TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def get_user():
    conn = _connect()
    row = conn.execute("SELECT id, username, password_hash, salt FROM users LIMIT 1").fetchone()
    conn.close()
    return row


def create_user(username: str, password_hash: str, salt: str):
    conn = _connect()
    conn.execute(
        "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
        (username, password_hash, salt, datetime.datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_category_assignments() -> dict:
    conn = _connect()
    rows = conn.execute("SELECT barcode, category_name FROM category_assignments").fetchall()
    conn.close()
    return {barcode: category for barcode, category in rows}


def save_category_assignments(assignments: dict):
    conn = _connect()
    conn.execute("DELETE FROM category_assignments")
    conn.executemany(
        "INSERT INTO category_assignments (barcode, category_name) VALUES (?, ?)",
        list(assignments.items()),
    )
    conn.commit()
    conn.close()
