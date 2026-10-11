from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class StorageError(RuntimeError):
    pass


class SessionStore:
    """Cada operacao abre a sua ligacao SQLite, permitindo workers independentes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
                    origin TEXT NOT NULL, label TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_calls (
                    id INTEGER PRIMARY KEY, timestamp REAL NOT NULL, day TEXT NOT NULL,
                    cache_key TEXT NOT NULL, result TEXT
                );
                CREATE INDEX IF NOT EXISTS ai_cache ON ai_calls(cache_key);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, session: dict, label: str = "Sessao") -> int:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO sessions(created_at, origin, label, payload) VALUES(?,?,?,?)",
                (session["created_at"], "Emulador" if session["simulation"] else "Veiculo real", label,
                 json.dumps(session, ensure_ascii=False, allow_nan=False)),
            )
            return int(cursor.lastrowid)

    def list_sessions(self) -> list[dict]:
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT id, created_at, origin, label FROM sessions ORDER BY id DESC")]

    def load(self, session_id: int) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            raise StorageError("Sessao nao encontrada.")
        return json.loads(row[0])

    def export(self, session_id: int, path: Path) -> None:
        path.write_text(json.dumps(self.load(session_id), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    def cache_get(self, key: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT result FROM ai_calls WHERE cache_key=? AND result IS NOT NULL ORDER BY id DESC LIMIT 1", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def reserve_call(self, key: str, timestamp: float, daily_limit: int, interval: int) -> int:
        day = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM ai_calls WHERE day=?", (day,)).fetchone()[0]
            last = db.execute("SELECT MAX(timestamp) FROM ai_calls").fetchone()[0]
            if count >= daily_limit:
                raise StorageError("Limite local diario de chamadas atingido (dia UTC).")
            if last is not None and timestamp - last < interval:
                raise StorageError("Aguarde o intervalo minimo entre chamadas Gemini.")
            cursor = db.execute("INSERT INTO ai_calls(timestamp, day, cache_key) VALUES(?,?,?)", (timestamp, day, key))
            return int(cursor.lastrowid)

    def cache_put(self, call_id: int, result: dict) -> None:
        with self.connect() as db:
            db.execute("UPDATE ai_calls SET result=? WHERE id=?", (json.dumps(result, ensure_ascii=False), call_id))
