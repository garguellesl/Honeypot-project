"""
logger.py
Capa de persistencia para los intentos de conexión capturados por el honeypot.
Usa SQLite porque es suficiente para un honeypot doméstico (sin dependencias
externas) y porque el dashboard puede leer directamente del mismo fichero.
"""

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "honeypot.db"

_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea la tabla de intentos si no existe. Llamar una vez al arrancar."""
    with _lock:
        conn = _get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                protocol TEXT NOT NULL,
                src_ip TEXT NOT NULL,
                src_port INTEGER,
                username TEXT,
                password TEXT,
                country TEXT,
                city TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON attempts(timestamp)"
        )
        conn.commit()
        conn.close()


def log_attempt(
    protocol: str,
    src_ip: str,
    src_port: int,
    username: str = "",
    password: str = "",
    country: str = "Unknown",
    city: str = "Unknown",
) -> None:
    """Inserta un intento de conexión/autenticación capturado."""
    timestamp = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = _get_connection()
        conn.execute(
            """
            INSERT INTO attempts
                (timestamp, protocol, src_ip, src_port, username, password, country, city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, protocol, src_ip, src_port, username, password, country, city),
        )
        conn.commit()
        conn.close()
    print(f"[{timestamp}] {protocol} {src_ip}:{src_port} user={username!r} pass={password!r}")


def get_recent_attempts(limit: int = 50):
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM attempts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = _get_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM attempts").fetchone()["c"]
    unique_ips = conn.execute(
        "SELECT COUNT(DISTINCT src_ip) AS c FROM attempts"
    ).fetchone()["c"]
    by_protocol = conn.execute(
        "SELECT protocol, COUNT(*) AS c FROM attempts GROUP BY protocol"
    ).fetchall()
    top_credentials = conn.execute(
        """
        SELECT username, password, COUNT(*) AS c
        FROM attempts
        WHERE username != '' OR password != ''
        GROUP BY username, password
        ORDER BY c DESC
        LIMIT 10
        """
    ).fetchall()
    top_ips = conn.execute(
        """
        SELECT src_ip, country, COUNT(*) AS c
        FROM attempts
        GROUP BY src_ip
        ORDER BY c DESC
        LIMIT 10
        """
    ).fetchall()
    timeline = conn.execute(
        """
        SELECT substr(timestamp, 1, 13) AS hour, COUNT(*) AS c
        FROM attempts
        GROUP BY hour
        ORDER BY hour DESC
        LIMIT 24
        """
    ).fetchall()
    conn.close()
    return {
        "total": total,
        "unique_ips": unique_ips,
        "by_protocol": [dict(r) for r in by_protocol],
        "top_credentials": [dict(r) for r in top_credentials],
        "top_ips": [dict(r) for r in top_ips],
        "timeline": [dict(r) for r in reversed(timeline)],
    }
