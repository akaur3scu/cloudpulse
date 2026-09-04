"""SQLite persistence for the local CloudPulse application."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path

from backend.monitor import utc_now

DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / "cloudpulse.db"


class DuplicateEndpointError(ValueError):
    pass


class Store:
    def __init__(self, database: str | Path = DEFAULT_DATABASE):
        self.database = str(database)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS endpoints (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint_id TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('online', 'offline')),
                    status_code INTEGER,
                    response_time_ms REAL,
                    error TEXT,
                    FOREIGN KEY(endpoint_id) REFERENCES endpoints(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS checks_endpoint_time
                    ON checks(endpoint_id, checked_at DESC);
                """
            )

    def add_endpoint(self, name: str, url: str) -> dict:
        endpoint = {
            "id": str(uuid.uuid4()),
            "name": name,
            "url": url,
            "created_at": utc_now(),
        }
        try:
            with self.connect() as connection:
                connection.execute(
                    "INSERT INTO endpoints (id, name, url, created_at) VALUES (?, ?, ?, ?)",
                    tuple(endpoint.values()),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateEndpointError("That URL is already being monitored.") from error
        return endpoint

    def delete_endpoint(self, endpoint_id: str) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM endpoints WHERE id = ?", (endpoint_id,)
            )
        return cursor.rowcount > 0

    def get_endpoints(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, name, url, created_at FROM endpoints ORDER BY created_at"
            ).fetchall()
        return [dict(row) for row in rows]

    def add_check(self, endpoint_id: str, result: dict) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO checks (
                    endpoint_id, checked_at, status, status_code,
                    response_time_ms, error
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    endpoint_id,
                    result["checked_at"],
                    result["status"],
                    result.get("status_code"),
                    result.get("response_time_ms"),
                    result.get("error"),
                ),
            )

    def list_services(self, history_limit: int = 20) -> list[dict]:
        services = self.get_endpoints()
        with self.connect() as connection:
            for service in services:
                rows = connection.execute(
                    """
                    SELECT checked_at, status, status_code, response_time_ms, error
                    FROM checks
                    WHERE endpoint_id = ?
                    ORDER BY checked_at DESC
                    LIMIT ?
                    """,
                    (service["id"], history_limit),
                ).fetchall()
                service["history"] = [dict(row) for row in reversed(rows)]
        return services
