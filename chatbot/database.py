"""Lapisan akses SQLite untuk riwayat dan statistik CurryCoach."""
from __future__ import annotations
import sqlite3
import uuid
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
CREATE TABLE IF NOT EXISTS pola_tambahan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT NOT NULL,
    pattern TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(tag, pattern)
);
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
CREATE TABLE IF NOT EXISTS telegram_users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL DEFAULT '',
    first_name TEXT NOT NULL DEFAULT '',
    active_session_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id TEXT PRIMARY KEY,
    telegram_id INTEGER NOT NULL REFERENCES telegram_users(telegram_id),
    label TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    last_used_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(telegram_id, created_at);
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


def sesi_aktif_telegram(database: str | Path, telegram_id: int,
                        username: str = "", first_name: str = "") -> str:
    """Ambil session_id aktif dari user Telegram; buat bila belum ada."""
    telegram_id = int(telegram_id)
    with get_connection(database) as connection:
        baris = connection.execute(
            "SELECT active_session_id FROM telegram_users WHERE telegram_id = ?",
            (telegram_id,),
        ).fetchone()
        if baris:
            session_id = baris["active_session_id"]
            connection.execute(
                """UPDATE telegram_users
                   SET username = ?, first_name = ?,
                       updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
                   WHERE telegram_id = ?""",
                (str(username or ""), str(first_name or ""), telegram_id),
            )
            connection.execute(
                """UPDATE chat_sessions
                   SET last_used_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
                   WHERE session_id = ?""",
                (session_id,),
            )
            return session_id
        session_id = str(uuid.uuid4())
        connection.execute(
            """INSERT INTO telegram_users
               (telegram_id, username, first_name, active_session_id)
               VALUES (?, ?, ?, ?)""",
            (telegram_id, str(username or ""), str(first_name or ""), session_id),
        )
        connection.execute(
            """INSERT INTO chat_sessions
               (session_id, telegram_id, label) VALUES (?, ?, ?)""",
            (session_id, telegram_id, "Sesi 1"),
        )
        return session_id


def daftar_sesi_telegram(database: str | Path, telegram_id: int) -> list[dict]:
    """Semua sesi milik satu user Telegram beserta jumlah pesannya."""
    with get_connection(database) as connection:
        rows = connection.execute(
            """SELECT s.session_id, s.label, s.created_at, s.last_used_at,
                      u.active_session_id,
                      (SELECT COUNT(*) FROM messages AS m
                       WHERE m.session_id = s.session_id) AS jumlah_pesan
               FROM chat_sessions AS s
               JOIN telegram_users AS u ON u.telegram_id = s.telegram_id
               WHERE s.telegram_id = ?
               ORDER BY s.created_at, s.rowid""",
            (int(telegram_id),),
        ).fetchall()
    hasil = [dict(row) for row in rows]
    for item in hasil:
        item["aktif"] = item["session_id"] == item["active_session_id"]
    return hasil


def info_sesi_aktif(database: str | Path, telegram_id: int) -> dict:
    """Detail sesi yang sedang aktif untuk user Telegram."""
    session_id = sesi_aktif_telegram(database, telegram_id)
    for item in daftar_sesi_telegram(database, telegram_id):
        if item["session_id"] == session_id:
            return item
    return {"session_id": session_id, "label": "Sesi 1", "jumlah_pesan": 0,
            "aktif": True}


def sesi_baru_telegram(database: str | Path, telegram_id: int) -> tuple[str, str]:
    """Buat sesi baru, jadikan aktif, dan kembalikan (session_id, label)."""
    sesi_aktif_telegram(database, telegram_id)
    with get_connection(database) as connection:
        jumlah = connection.execute(
            "SELECT COUNT(*) FROM chat_sessions WHERE telegram_id = ?",
            (int(telegram_id),),
        ).fetchone()[0]
        session_id = str(uuid.uuid4())
        label = f"Sesi {jumlah + 1}"
        connection.execute(
            """INSERT INTO chat_sessions
               (session_id, telegram_id, label) VALUES (?, ?, ?)""",
            (session_id, int(telegram_id), label),
        )
        connection.execute(
            """UPDATE telegram_users
               SET active_session_id = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
               WHERE telegram_id = ?""",
            (session_id, int(telegram_id)),
        )
    return session_id, label


def pilih_sesi_telegram(database: str | Path, telegram_id: int,
                        nomor: int | str) -> dict | None:
    """Ganti sesi aktif berdasarkan nomor urut dari /session."""
    try:
        nomor = int(nomor)
    except (TypeError, ValueError):
        return None
    daftar = daftar_sesi_telegram(database, telegram_id)
    if not 1 <= nomor <= len(daftar):
        return None
    pilihan = daftar[nomor - 1]
    with get_connection(database) as connection:
        connection.execute(
            """UPDATE telegram_users
               SET active_session_id = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
               WHERE telegram_id = ?""",
            (pilihan["session_id"], int(telegram_id)),
        )
        connection.execute(
            """UPDATE chat_sessions
               SET last_used_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
               WHERE session_id = ?""",
            (pilihan["session_id"],),
        )
    pilihan["aktif"] = True
    return pilihan


# ---------------------------------------------------------------------------
# Pengelolaan data oleh admin (CRUD latihan dan pola tambahan)
# ---------------------------------------------------------------------------
def daftar_latihan_admin(database: str | Path, q: str | None = None,
                         limit: int = 50, offset: int = 0) -> dict:
    """Daftar latihan untuk halaman admin, dengan pencarian nama dan paging."""
    kondisi, params = "", []
    if q:
        kondisi = "WHERE name LIKE ? OR category LIKE ?"
        params = [f"%{q}%", f"%{q}%"]
    with get_connection(database) as connection:
        total = connection.execute(
            f"SELECT COUNT(*) FROM exercises {kondisi}", params).fetchone()[0]
        rows = connection.execute(
            f"""SELECT id, name, category, equipment, muscles, level, description, source
                FROM exercises {kondisi} ORDER BY id DESC LIMIT ? OFFSET ?""",
            params + [max(1, min(int(limit), 100)), max(0, int(offset))],
        ).fetchall()
    return {"total": int(total), "items": [dict(row) for row in rows]}


def tambah_latihan(database: str | Path, data: dict) -> int:
    """Tambah latihan buatan admin (tanpa ID eksternal, sumber 'manual')."""
    with get_connection(database) as connection:
        cursor = connection.execute(
            """INSERT INTO exercises
               (external_id, name, category, equipment, muscles, level, description, source)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, 'manual')""",
            (data["name"], data["category"], data["equipment"], data["muscles"],
             data["level"], data["description"]),
        )
        return int(cursor.lastrowid)


def ubah_latihan(database: str | Path, exercise_id: int, data: dict) -> bool:
    """Perbarui latihan. Mengembalikan False jika ID tidak ada."""
    with get_connection(database) as connection:
        cursor = connection.execute(
            """UPDATE exercises SET name=?, category=?, equipment=?, muscles=?,
                      level=?, description=? WHERE id=?""",
            (data["name"], data["category"], data["equipment"], data["muscles"],
             data["level"], data["description"], int(exercise_id)),
        )
        return cursor.rowcount > 0


def hapus_latihan(database: str | Path, exercise_id: int) -> str:
    """Hapus latihan. Hasil: 'ok', 'tidak_ada', atau 'dipakai' (sudah ada di catatan sesi)."""
    with get_connection(database) as connection:
        ada = connection.execute(
            "SELECT 1 FROM exercises WHERE id = ?", (int(exercise_id),)).fetchone()
        if not ada:
            return "tidak_ada"
        dipakai = connection.execute(
            "SELECT 1 FROM workout_sessions WHERE exercise_id = ? LIMIT 1",
            (int(exercise_id),)).fetchone()
        if dipakai:
            return "dipakai"
        connection.execute("DELETE FROM exercises WHERE id = ?", (int(exercise_id),))
        return "ok"


def ambil_pola_tambahan(database: str | Path) -> list[dict]:
    with get_connection(database) as connection:
        rows = connection.execute(
            "SELECT id, tag, pattern, created_at FROM pola_tambahan ORDER BY id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def simpan_pola_tambahan(database: str | Path, tag: str, pattern: str) -> int:
    """Simpan pola baru untuk sebuah intent. Mengembalikan ID baris baru."""
    with get_connection(database) as connection:
        cursor = connection.execute(
            "INSERT INTO pola_tambahan (tag, pattern) VALUES (?, ?)", (tag, pattern))
        return int(cursor.lastrowid)


def hapus_pola_tambahan(database: str | Path, pola_id: int) -> bool:
    with get_connection(database) as connection:
        cursor = connection.execute(
            "DELETE FROM pola_tambahan WHERE id = ?", (int(pola_id),))
        return cursor.rowcount > 0
