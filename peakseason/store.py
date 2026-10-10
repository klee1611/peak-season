"""SQLite cache and state. Losing this file is harmless: it only causes re-classification.

It is never the source of truth for the SerpApi budget (that is SerpApi's Account API).
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS classifications (
    key TEXT PRIMARY KEY,          -- sha256(item + target + prompt version)
    target_id TEXT NOT NULL,
    item TEXT NOT NULL,            -- photo URL or text snippet id
    status TEXT NOT NULL,          -- ok | rejected | unclassified
    stage TEXT,
    progress REAL,
    confidence REAL,
    model TEXT,
    latency_s REAL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS serpapi_cache (
    target_id TEXT NOT NULL,
    spot_id TEXT NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    PRIMARY KEY (target_id, spot_id, query)
);
CREATE TABLE IF NOT EXISTS serpapi_usage (
    at REAL NOT NULL,
    target_id TEXT NOT NULL,
    spot_id TEXT NOT NULL,
    query TEXT NOT NULL,
    status TEXT NOT NULL
);
"""


@dataclass
class Classification:
    status: str
    stage: str | None
    progress: float | None
    confidence: float | None


class Store:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # Classification cache
    def get_classification(self, key: str) -> Classification | None:
        row = self.db.execute(
            "SELECT status, stage, progress, confidence FROM classifications WHERE key = ?",
            (key,),
        ).fetchone()
        return Classification(*row) if row else None

    def put_classification(
        self,
        key: str,
        target_id: str,
        item: str,
        result: Classification,
        model: str,
        latency_s: float,
    ) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO classifications VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                key,
                target_id,
                item,
                result.status,
                result.stage,
                result.progress,
                result.confidence,
                model,
                latency_s,
                time.time(),
            ),
        )
        self.db.commit()

    # Small JSON key/value cache (resolved taxa, controlled terms)
    def get_json(self, key: str, max_age_s: float | None = None):
        row = self.db.execute("SELECT value, updated_at FROM kv WHERE key = ?", (key,)).fetchone()
        if not row or (max_age_s is not None and time.time() - row[1] > max_age_s):
            return None
        return json.loads(row[0])

    def put_json(self, key: str, value) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO kv VALUES (?,?,?)",
            (key, json.dumps(value, ensure_ascii=False), time.time()),
        )
        self.db.commit()

    # SerpApi
    def get_serpapi(self, target_id: str, spot_id: str, query: str, max_age_s: float):
        row = self.db.execute(
            "SELECT response, fetched_at FROM serpapi_cache "
            "WHERE target_id = ? AND spot_id = ? AND query = ?",
            (target_id, spot_id, query),
        ).fetchone()
        if not row or time.time() - row[1] > max_age_s:
            return None
        return json.loads(row[0])

    def put_serpapi(self, target_id: str, spot_id: str, query: str, response: dict) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO serpapi_cache VALUES (?,?,?,?,?)",
            (target_id, spot_id, query, json.dumps(response, ensure_ascii=False), time.time()),
        )
        self.db.commit()

    def log_serpapi(self, target_id: str, spot_id: str, query: str, status: str) -> None:
        self.db.execute(
            "INSERT INTO serpapi_usage VALUES (?,?,?,?,?)",
            (time.time(), target_id, spot_id, query, status),
        )
        self.db.commit()
