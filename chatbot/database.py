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
CREATE TABLE IF NOT EXISTS referensi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT NOT NULL,
    paragraph TEXT NOT NULL,
    extracted_at TEXT,
    UNIQUE(source_url, paragraph)
);
CREATE INDEX IF NOT EXISTS idx_referensi_title ON referensi(title);
CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id INTEGER UNIQUE,
    name TEXT NOT NULL,
    category TEXT,
    equipment TEXT,
    muscles TEXT,
    level TEXT,
    description TEXT,
    source TEXT NOT NULL DEFAULT 'wger'
);
CREATE INDEX IF NOT EXISTS idx_exercises_filter ON exercises(category, equipment, level);
CREATE TABLE IF NOT EXISTS workout_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    duration_min INTEGER NOT NULL CHECK(duration_min > 0),
    shots_made INTEGER NOT NULL DEFAULT 0 CHECK(shots_made >= 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON workout_sessions(telegram_id, created_at);
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


def simpan_referensi(database: str | Path, records: list[dict]) -> int:
    """Simpan paragraf hasil scraping; duplikat diabaikan."""
    data = [
        (item.get("source_url", ""), item.get("domain", ""),
         item.get("title", ""), item.get("paragraph", ""),
         item.get("extracted_at", ""))
        for item in records if item.get("paragraph", "").strip()
    ]
    with get_connection(database) as connection:
        sebelum = connection.total_changes
        connection.executemany(
            """INSERT OR IGNORE INTO referensi
               (source_url, domain, title, paragraph, extracted_at)
               VALUES (?, ?, ?, ?, ?)""",
            data,
        )
        return connection.total_changes - sebelum


def ambil_referensi(database: str | Path, limit: int = 500) -> list[dict]:
    """Ambil paragraf referensi untuk korpus TF-IDF."""
    with get_connection(database) as connection:
        rows = connection.execute(
            """SELECT source_url, title, paragraph FROM referensi
               ORDER BY id LIMIT ?""",
            (max(1, min(int(limit), 2000)),),
        ).fetchall()
    return [dict(row) for row in rows]


def simpan_latihan(database: str | Path, exercises: list[dict]) -> int:
    """Simpan atau perbarui katalog latihan berdasarkan ID eksternal."""
    data = [
        (item.get("external_id"), item.get("name", ""), item.get("category", ""),
         item.get("equipment", ""), item.get("muscles", ""), item.get("level", ""),
         item.get("description", ""), item.get("source", "wger"))
        for item in exercises if item.get("name", "").strip()
    ]
    with get_connection(database) as connection:
        sebelum = connection.total_changes
        connection.executemany(
            """INSERT INTO exercises
               (external_id, name, category, equipment, muscles, level,
                description, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(external_id) DO UPDATE SET
                 name=excluded.name, category=excluded.category,
                 equipment=excluded.equipment, muscles=excluded.muscles,
                 level=excluded.level, description=excluded.description,
                 source=excluded.source""",
            data,
        )
        return connection.total_changes - sebelum


def cari_latihan(database: str | Path, level: str | None = None,
                 alat: str | None = None, otot: str | None = None,
                 limit: int = 5) -> list[dict]:
    """Cari katalog latihan dengan filter level, alat, dan otot."""
    klausa, nilai = [], []
    if level:
        klausa.append("lower(level) = ?")
        nilai.append(str(level).strip().lower())
    if alat:
        if str(alat).strip().lower() in {"tanpa alat", "no equipment", "none"}:
            klausa.append(
                "(equipment IS NULL OR trim(equipment) = '' "
                "OR lower(equipment) IN ('none', 'tanpa alat'))"
            )
        else:
            klausa.append("lower(equipment) LIKE ?")
            nilai.append(f"%{str(alat).strip().lower()}%")
    if otot:
        klausa.append("(lower(muscles) LIKE ? OR lower(category) LIKE ?)")
        nilai.extend([f"%{str(otot).strip().lower()}%"] * 2)
    where = " WHERE " + " AND ".join(klausa) if klausa else ""
    nilai.append(max(1, min(int(limit), 20)))
    with get_connection(database) as connection:
        rows = connection.execute(
            "SELECT id, name, category, equipment, muscles, level, description "
            f"FROM exercises{where} ORDER BY id LIMIT ?",
            nilai,
        ).fetchall()
    return [dict(row) for row in rows]


def ambil_latihan(database: str | Path, exercise_id: int) -> dict | None:
    with get_connection(database) as connection:
        row = connection.execute(
            "SELECT id, name, category, level FROM exercises WHERE id = ?",
            (int(exercise_id),),
        ).fetchone()
    return dict(row) if row else None


def simpan_sesi_latihan(database: str | Path, telegram_id: int,
                        exercise_id: int, duration_min: int,
                        shots_made: int = 0) -> int:
    """Catat satu sesi latihan milik pengguna (ID Telegram)."""
    with get_connection(database) as connection:
        cursor = connection.execute(
            """INSERT INTO workout_sessions
               (telegram_id, exercise_id, duration_min, shots_made)
               VALUES (?, ?, ?, ?)""",
            (int(telegram_id), int(exercise_id), int(duration_min), int(shots_made)),
        )
        return int(cursor.lastrowid)


def ambil_sesi_latihan(database: str | Path, telegram_id: int,
                       limit: int = 20) -> list[dict]:
    with get_connection(database) as connection:
        rows = connection.execute(
            """SELECT s.id, s.duration_min, s.shots_made, s.created_at,
                      e.name AS exercise_name, e.category
               FROM workout_sessions AS s
               JOIN exercises AS e ON e.id = s.exercise_id
               WHERE s.telegram_id = ? ORDER BY s.id DESC LIMIT ?""",
            (int(telegram_id), max(1, min(int(limit), 100))),
        ).fetchall()
    return [dict(row) for row in rows]


def data_sesi_latihan(database: str | Path, telegram_id: int,
                      days: int = 7) -> list[dict]:
    """Data mentah sesi untuk diolah pandas."""
    with get_connection(database) as connection:
        rows = connection.execute(
            """SELECT date(s.created_at) AS tanggal, e.category AS kategori,
                      s.duration_min AS durasi, s.shots_made AS tembakan
               FROM workout_sessions AS s
               JOIN exercises AS e ON e.id = s.exercise_id
               WHERE s.telegram_id = ?
                 AND s.created_at >= datetime('now', ?)
               ORDER BY s.created_at""",
            (int(telegram_id), f"-{int(days)} days"),
        ).fetchall()
    return [dict(row) for row in rows]


def pengguna_perlu_pengingat(database: str | Path, hari: int = 2) -> list[int]:
    """ID Telegram yang belum berlatih selama minimal `hari` hari."""
    with get_connection(database) as connection:
        rows = connection.execute(
            """SELECT telegram_id, MAX(created_at) AS terakhir
               FROM workout_sessions GROUP BY telegram_id
               HAVING date(terakhir) < date('now', ?)""",
            (f"-{int(hari)} days",),
        ).fetchall()
    return [int(row["telegram_id"]) for row in rows]
