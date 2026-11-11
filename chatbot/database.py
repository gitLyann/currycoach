"""Lapisan akses SQLite untuk riwayat dan statistik CurryCoach."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    theme TEXT NOT NULL,
    sender TEXT NOT NULL CHECK(sender IN ('user', 'bot')),
    text TEXT NOT NULL,
    intent TEXT,
    score REAL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session_theme_id
ON messages(session_id, theme, id);
CREATE INDEX IF NOT EXISTS idx_messages_theme_intent
ON messages(theme, intent);
"""


@contextmanager
def get_connection(database: str | Path):
    """Kelola koneksi SQLite dan pastikan koneksi selalu ditutup."""
    connection = sqlite3.connect(str(database), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(database: str | Path) -> None:
    """Buat tabel dan indeks jika belum tersedia."""
    path = Path(database)
    if str(database) != ':memory:':
        path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(database) as connection:
        connection.executescript(SCHEMA)


def simpan_pesan(database: str | Path, session_id: str, theme: str,
                 sender: str, text: str, intent: str | None = None,
                 score: float | None = None) -> int:
    """Simpan satu pesan dan kembalikan ID baris."""
    with get_connection(database) as connection:
        cursor = connection.execute(
            """INSERT INTO messages
               (session_id, theme, sender, text, intent, score)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, theme, sender, text, intent, score),
        )
        return int(cursor.lastrowid)


def ambil_riwayat(database: str | Path, session_id: str, theme: str,
                  limit: int = 100) -> list[dict]:
    """Ambil riwayat milik satu sesi saja, dari yang terlama ke terbaru."""
    with get_connection(database) as connection:
        rows = connection.execute(
            """SELECT id, sender, text, intent, score, created_at
               FROM messages WHERE session_id = ? AND theme = ?
               ORDER BY id DESC LIMIT ?""",
            (session_id, theme, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def hapus_riwayat(database: str | Path, session_id: str, theme: str) -> int:
    """Hapus riwayat hanya untuk sesi dan tema yang diminta."""
    with get_connection(database) as connection:
        cursor = connection.execute(
            "DELETE FROM messages WHERE session_id = ? AND theme = ?",
            (session_id, theme),
        )
        return cursor.rowcount


def statistik(database: str | Path, theme: str) -> dict:
    """Ringkasan statistik percakapan untuk tema."""
    with get_connection(database) as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM messages WHERE theme = ? AND sender = 'user'",
            (theme,),
        ).fetchone()[0]
        recognized = connection.execute(
            """SELECT COUNT(*) FROM messages
               WHERE theme = ? AND sender = 'bot' AND intent != 'fallback'""",
            (theme,),
        ).fetchone()[0]
        unrecognized = connection.execute(
            """SELECT COUNT(*) FROM messages
               WHERE theme = ? AND sender = 'bot' AND intent = 'fallback'""",
            (theme,),
        ).fetchone()[0]
        sessions = connection.execute(
            "SELECT COUNT(DISTINCT session_id) FROM messages WHERE theme = ?",
            (theme,),
        ).fetchone()[0]
        by_intent = connection.execute(
            """SELECT intent, COUNT(*) AS total FROM messages
               WHERE theme = ? AND sender = 'bot' AND intent IS NOT NULL
               GROUP BY intent ORDER BY total DESC, intent ASC""",
            (theme,),
        ).fetchall()
        unknown = connection.execute(
            """SELECT user_message.text, COUNT(*) AS total
               FROM messages AS bot_message
               JOIN messages AS user_message
                 ON user_message.session_id = bot_message.session_id
                AND user_message.theme = bot_message.theme
                AND user_message.sender = 'user'
                AND user_message.id < bot_message.id
               WHERE bot_message.theme = ?
                 AND bot_message.sender = 'bot'
                 AND bot_message.intent = 'fallback'
                 AND NOT EXISTS (
                     SELECT 1 FROM messages AS middle_message
                     WHERE middle_message.session_id = bot_message.session_id
                       AND middle_message.theme = bot_message.theme
                       AND middle_message.id > user_message.id
                       AND middle_message.id < bot_message.id
                 )
               GROUP BY user_message.text
               ORDER BY total DESC, user_message.text ASC LIMIT 20""",
            (theme,),
        ).fetchall()
    return {
        "total_questions": total,
        "recognized": recognized,
        "unrecognized": unrecognized,
        "sessions": sessions,
        "intent_stats": [dict(row) for row in by_intent],
        "unrecognized_questions": [dict(row) for row in unknown],
    }
