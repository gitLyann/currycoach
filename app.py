"""Aplikasi CurryCoach: edukasi basket pemula dengan Flask dan SQLite."""
from __future__ import annotations
import hmac
import os
import random
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from dotenv import load_dotenv
from chatbot.database import (
    ambil_pola_tambahan, ambil_riwayat, ambil_sesi_latihan, cari_latihan,
    daftar_latihan_admin, hapus_latihan, hapus_pola_tambahan, hapus_riwayat,
    init_db, simpan_pesan, simpan_pola_tambahan, statistik, tambah_latihan,
    ubah_latihan,
)
from chatbot.engine import (
    DEFAULT_THRESHOLD, cari_intent as _cari_intent, cari_intent_detail,
    muat_tema, normalisasi, tokenisasi,
)
from chatbot.handlers import jawaban_latihan
from chatbot.tautan import baca_token
from chatbot.tfidf import muat_mesin_dari_database
from analytics.laporan import (
    deret_harian, format_laporan, menit_per_kategori, ringkasan_mingguan,
)
from analytics.rekomendasi import format_rekomendasi, rekomendasi

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")
MAKS_PANJANG = 300
KUNCI_WAJIB = ["id", "name", "bot_name", "avatar", "color", "description",
               "greeting", "suggestions", "fallback", "intents"]


LEVEL_LATIHAN = ("pemula", "menengah", "lanjutan")
BATAS_TEKS = {"name": 100, "category": 50, "equipment": 50, "muscles": 100,
              "description": 1000}


def validasi_latihan(data) -> tuple[dict | None, list[str]]:
    """Periksa dan rapikan isian latihan dari admin. Mengembalikan (data, daftar_error)."""
    if not isinstance(data, dict):
        return None, ["Body harus berupa JSON object."]
    bersih, error = {}, []
    for kolom, batas in BATAS_TEKS.items():
        nilai = data.get(kolom, "")
        if not isinstance(nilai, str):
            error.append(f"{kolom} harus berupa teks.")
            continue
        nilai = nilai.strip()
        if len(nilai) > batas:
            error.append(f"{kolom} maksimal {batas} karakter.")
        bersih[kolom] = nilai
    for kolom in ("name", "category"):
        if not bersih.get(kolom):
            error.append(f"{kolom} wajib diisi.")
    level = str(data.get("level", "")).strip().lower()
    if level not in LEVEL_LATIHAN:
        error.append("level harus salah satu dari: " + ", ".join(LEVEL_LATIHAN) + ".")
    bersih["level"] = level
    return (None, error) if error else (bersih, [])


def validasi_tema(tema: dict) -> list:
    """Validasi struktur basis pengetahuan sesuai ketentuan proyek."""
    if not isinstance(tema, dict):
        return ["tema harus berupa objek JSON"]
    masalah = [f"kunci '{k}' tidak ada" for k in KUNCI_WAJIB if k not in tema]
    if masalah:
        return masalah
    if not isinstance(tema["intents"], list) or len(tema["intents"]) < 10:
        masalah.append("tema harus memiliki minimal 10 intent")
    if not isinstance(tema["fallback"], list) or not tema["fallback"]:
        masalah.append("daftar 'fallback' kosong atau bukan list")
    tags, pola_global = set(), {}
    for i, intent in enumerate(tema["intents"], start=1):
        if not isinstance(intent, dict):
            masalah.append(f"intent ke-{i} harus berupa objek")
            continue
        for key in ("tag", "patterns", "responses"):
            if not intent.get(key):
                masalah.append(f"intent ke-{i}: kunci '{key}' tidak ada atau kosong")
        tag = intent.get("tag", f"#{i}")
        if tag in tags:
            masalah.append(f"tag '{tag}' dipakai lebih dari sekali")
        tags.add(tag)
        patterns, responses = intent.get("patterns", []), intent.get("responses", [])
        if not isinstance(patterns, list) or len(patterns) < 5:
            masalah.append(f"intent '{tag}' harus memiliki minimal 5 patterns")
            patterns = patterns if isinstance(patterns, list) else []
        if not isinstance(responses, list) or len(responses) < 2:
            masalah.append(f"intent '{tag}' harus memiliki minimal 2 responses")
        for pola in patterns:
            kunci = normalisasi(pola)
            if kunci in pola_global and kunci and pola_global[kunci] != tag:
                masalah.append(f"pattern '{pola}' duplikat pada intent '{tag}' dan '{pola_global[kunci]}'")
            pola_global[kunci] = tag
    if not isinstance(tema.get("suggestions"), list) or len(tema["suggestions"]) < 4:
        masalah.append("tema harus memiliki minimal 4 suggestions")
    return masalah


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory agar konfigurasi dan database mudah diuji."""
    app = Flask(__name__)
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    secret_key = os.getenv("SECRET_KEY", "")
    admin_key = os.getenv("ADMIN_KEY", "")
    if app_env == "production":
        if not secret_key or secret_key.startswith("ganti-dengan"):
            raise RuntimeError("SECRET_KEY wajib diatur dengan nilai acak yang kuat di production.")
        if not admin_key or admin_key.startswith("ganti-dengan"):
            raise RuntimeError("ADMIN_KEY wajib diatur dengan nilai acak yang kuat di production.")

    app.config.from_mapping(
        SECRET_KEY=secret_key or "dev-only-change-this-secret",
        DATABASE=os.getenv("DATABASE", str(BASE / "instance" / "currycoach.sqlite3")),
        THRESHOLD=float(os.getenv("THRESHOLD", str(DEFAULT_THRESHOLD))),
        ADMIN_KEY=admin_key,
        MAX_CONTENT_LENGTH=16 * 1024,
        JSON_SORT_KEYS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
    )
    if test_config:
        app.config.update(test_config)

    tema = muat_tema()
    masalah = validasi_tema(tema)
    if masalah:
        raise ValueError("currycoach.json tidak valid:\n- " + "\n- ".join(masalah))
    intents = tema["intents"]
    theme_id = tema["id"]
    fallback = tema["fallback"]
    init_db(app.config["DATABASE"])
    mesin_tfidf = muat_mesin_dari_database(
        app.config["DATABASE"],
        limit=int(os.getenv("TFIDF_LIMIT", "500")),
        threshold=float(os.getenv("TFIDF_THRESHOLD", "0.22")),
    )

    def session_id() -> str:
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        return session["session_id"]

    def isi_placeholder(teks: str) -> str:
        return teks.replace("{nama_bot}", tema["bot_name"])

    def intents_aktif() -> list[dict]:
        """Intent dari currycoach.json digabung dengan pola tambahan buatan admin (database)."""
        tambahan = ambil_pola_tambahan(app.config["DATABASE"])
        if not tambahan:
            return intents
        peta: dict[str, list[str]] = {}
        for baris in tambahan:
            peta.setdefault(baris["tag"], []).append(baris["pattern"])
        return [dict(item, patterns=list(item["patterns"]) + peta.get(item["tag"], []))
                for item in intents]

    def proses_pesan(pesan: str, explain: bool = False,
                     sid_override: str | None = None,
                     simpan_riwayat: bool = True) -> dict:
        terbaik, kandidat = cari_intent_detail(
            pesan, intents_aktif(), float(app.config["THRESHOLD"])
        )
        referensi_terbaik = None
        if terbaik is None:
            referensi_terbaik = mesin_tfidf.cari(pesan, top_n=1)
            if referensi_terbaik:
                item = referensi_terbaik[0]
                potongan = item["text"][:240].rsplit(" ", 1)[0]
                intent_tag = "referensi"
                jawaban = (f"Dari referensi basket ({item['source']}): "
                           f"{potongan}...")
                score = item["score"]
            else:
                intent_tag = "fallback"
                jawaban = isi_placeholder(random.choice(fallback))
                score = round(kandidat[0]["score"], 4) if kandidat else 0.0
        else:
            intent_tag = terbaik["intent"]["tag"]
            jawaban = isi_placeholder(random.choice(terbaik["intent"]["responses"]))
            score = round(terbaik["score"], 4)
            if intent_tag == "program_latihan":
                tambahan = jawaban_latihan(app.config["DATABASE"], pesan)
                if tambahan:
                    jawaban = f"{jawaban}\n\n{tambahan}"

        sid = sid_override or session_id()
        if simpan_riwayat:
            simpan_pesan(app.config["DATABASE"], sid, theme_id, "user", pesan)
            simpan_pesan(app.config["DATABASE"], sid, theme_id, "bot", jawaban,
                         intent=intent_tag, score=score)
        hasil = {"reply": jawaban, "intent": intent_tag, "score": score}
        if referensi_terbaik:
            hasil["source"] = referensi_terbaik[0]["source"]
        if explain:
            hasil["candidates"] = [
                {"intent": item["tag"], "score": round(item["score"], 4),
                 "pattern": item["pattern"], "details": {
                     key: round(value, 4) for key, value in item["details"].items()
                 }}
                for item in kandidat[:5]
            ]
            hasil["threshold"] = float(app.config["THRESHOLD"])
        return hasil

    def validasi_pesan():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return None, (jsonify(error="Body harus berupa JSON object."), 400)
        pesan = data.get("message", "")
        if not isinstance(pesan, str):
            return None, (jsonify(error="Pesan harus berupa teks."), 400)
        pesan = pesan.strip()
        if not pesan:
            return None, (jsonify(error="Pesan tidak boleh kosong."), 400)
        if len(pesan) > MAKS_PANJANG:
            return None, (jsonify(error=f"Pesan maksimal {MAKS_PANJANG} karakter."), 413)
        return pesan, None

    def admin_diizinkan():
        key = app.config.get("ADMIN_KEY", "")
        # Mode pengembangan tanpa ADMIN_KEY; produksi sebaiknya mengaturnya.
        if not key:
            return True
        supplied = request.headers.get("X-Admin-Key", "")
        return hmac.compare_digest(str(supplied), str(key))

    @app.get("/")
    def index():
        return render_template("index.html", tema=tema)

    @app.get("/chat/<theme>")
    def halaman_chat(theme):
        if theme != theme_id:
            return jsonify(error="Tema tidak ditemukan."), 404
        return render_template("index.html", tema=tema)

    @app.get("/admin")
    def halaman_admin():
        # Data statistik tetap dilindungi oleh ADMIN_KEY pada endpoint API.
        return render_template("admin.html", tema=tema)

    @app.get("/api/themes")
    def daftar_tema():
        return jsonify(themes=[{
            "id": tema["id"], "name": tema["name"],
            "description": tema["description"], "avatar": tema["avatar"],
            "color": tema["color"],
        }])

    # Endpoint lama tetap tersedia agar frontend dan pengujian sebelumnya kompatibel.
    @app.post("/chat")
    def chat_lama():
        pesan, error = validasi_pesan()
        if error:
            return error
        return jsonify(proses_pesan(pesan))

    @app.post("/api/chat")
    def api_chat():
        pesan, error = validasi_pesan()
        if error:
            return error
        data = request.get_json(silent=True) or {}
        requested_theme = data.get("theme", theme_id)
        if requested_theme != theme_id:
            return jsonify(error="Tema tidak ditemukan."), 404
        sid_override = data.get("session_id")
        if sid_override is not None:
            if not isinstance(sid_override, str):
                return jsonify(error="session_id harus berupa teks."), 400
            try:
                uuid.UUID(sid_override)
            except ValueError:
                return jsonify(error="session_id tidak valid."), 400
        simpan_riwayat = data.get("simpan_riwayat", True)
        if not isinstance(simpan_riwayat, bool):
            return jsonify(error="simpan_riwayat harus berupa boolean."), 400
        return jsonify(proses_pesan(pesan, sid_override=sid_override,
                                    simpan_riwayat=simpan_riwayat))

    @app.post("/api/explain")
    def api_explain():
        pesan, error = validasi_pesan()
        if error:
            return error
        data = request.get_json(silent=True) or {}
        if data.get("theme", theme_id) != theme_id:
            return jsonify(error="Tema tidak ditemukan."), 404
        return jsonify(proses_pesan(pesan, explain=True))

    @app.get("/api/history/<theme>")
    def api_history(theme):
        if theme != theme_id:
            return jsonify(error="Tema tidak ditemukan."), 404
        try:
            limit = min(max(int(request.args.get("limit", 100)), 1), 200)
        except ValueError:
            return jsonify(error="Parameter limit harus berupa angka."), 400
        history = ambil_riwayat(app.config["DATABASE"], session_id(), theme, limit)
        return jsonify(theme=theme, messages=history, count=len(history))

    @app.delete("/api/history/<theme>")
    def api_hapus_history(theme):
        if theme != theme_id:
            return jsonify(error="Tema tidak ditemukan."), 404
        jumlah = hapus_riwayat(app.config["DATABASE"], session_id(), theme)
        return jsonify(message="Riwayat berhasil dihapus.", deleted=jumlah)

    @app.get("/api/stats/<theme>")
    def api_stats(theme):
        if theme != theme_id:
            return jsonify(error="Tema tidak ditemukan."), 404
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        return jsonify(theme=theme, **statistik(app.config["DATABASE"], theme))

    @app.get("/api/latihan")
    def api_latihan():
        try:
            limit = min(max(int(request.args.get("limit", 5)), 1), 20)
        except ValueError:
            return jsonify(error="Parameter limit harus berupa angka."), 400
        items = cari_latihan(
            app.config["DATABASE"],
            level=request.args.get("level"),
            alat=request.args.get("alat"),
            otot=request.args.get("otot"),
            limit=limit,
        )
        return jsonify(count=len(items), latihan=items)

    @app.get("/api/laporan/<int:telegram_id>")
    def api_laporan(telegram_id):
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        ringkasan = ringkasan_mingguan(app.config["DATABASE"], telegram_id)
        saran = rekomendasi(app.config["DATABASE"], telegram_id, ringkasan)
        return jsonify(
            ringkasan=ringkasan, saran=saran,
            teks=format_laporan(ringkasan) + "\n" + format_rekomendasi(saran),
        )

    # ------------------------------------------------------------------
    # Halaman katalog latihan dan dashboard latihan pribadi
    # ------------------------------------------------------------------
    @app.get("/katalog")
    def halaman_katalog():
        return render_template("katalog.html", tema=tema)

    @app.get("/progres")
    def halaman_progres():
        # Token diperiksa oleh /api/progres; halaman hanya kerangka tampilan.
        return render_template("progres.html", tema=tema)

    @app.get("/api/progres")
    def api_progres():
        telegram_id = baca_token(app.config["SECRET_KEY"], request.args.get("t", ""))
        if telegram_id is None:
            return jsonify(error="Tautan tidak valid atau sudah kedaluwarsa. "
                                 "Ketik /dashboard di Telegram untuk membuat yang baru."), 401
        db = app.config["DATABASE"]
        ringkasan_7 = ringkasan_mingguan(db, telegram_id, 7)
        ringkasan_30 = ringkasan_mingguan(db, telegram_id, 30)
        return jsonify(
            ringkasan_7=ringkasan_7,
            ringkasan_30=ringkasan_30,
            harian=deret_harian(ringkasan_30, 14),
            kategori=menit_per_kategori(db, telegram_id, 30),
            sesi_terbaru=ambil_sesi_latihan(db, telegram_id, 8),
            saran=rekomendasi(db, telegram_id, ringkasan_7),
        )

    # ------------------------------------------------------------------
    # Pengelolaan data oleh admin: latihan dan pola tambahan
    # ------------------------------------------------------------------
    @app.get("/admin/kelola")
    def halaman_kelola():
        return render_template("admin_kelola.html", tema=tema,
                               tag_intent=[i["tag"] for i in intents])

    @app.get("/api/admin/latihan")
    def admin_daftar_latihan():
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        try:
            limit = int(request.args.get("limit", 20))
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return jsonify(error="limit dan offset harus berupa angka."), 400
        return jsonify(**daftar_latihan_admin(
            app.config["DATABASE"], request.args.get("q", "").strip() or None, limit, offset))

    @app.post("/api/admin/latihan")
    def admin_tambah_latihan():
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        data, error = validasi_latihan(request.get_json(silent=True))
        if error:
            return jsonify(error="Data tidak valid.", detail=error), 400
        return jsonify(id=tambah_latihan(app.config["DATABASE"], data)), 201

    @app.put("/api/admin/latihan/<int:exercise_id>")
    def admin_ubah_latihan(exercise_id):
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        data, error = validasi_latihan(request.get_json(silent=True))
        if error:
            return jsonify(error="Data tidak valid.", detail=error), 400
        if not ubah_latihan(app.config["DATABASE"], exercise_id, data):
            return jsonify(error="Latihan tidak ditemukan."), 404
        return jsonify(id=exercise_id)

    @app.delete("/api/admin/latihan/<int:exercise_id>")
    def admin_hapus_latihan(exercise_id):
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        hasil = hapus_latihan(app.config["DATABASE"], exercise_id)
        if hasil == "tidak_ada":
            return jsonify(error="Latihan tidak ditemukan."), 404
        if hasil == "dipakai":
            return jsonify(error="Latihan sudah dipakai di catatan sesi pengguna, "
                                 "jadi tidak dapat dihapus."), 409
        return jsonify(id=exercise_id)

    @app.get("/api/admin/pola")
    def admin_daftar_pola():
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        return jsonify(pola=ambil_pola_tambahan(app.config["DATABASE"]),
                       tag=[i["tag"] for i in intents])

    @app.post("/api/admin/pola")
    def admin_tambah_pola():
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="Body harus berupa JSON object."), 400
        tag = str(data.get("tag", "")).strip()
        pola = str(data.get("pattern", "")).strip()
        if tag not in {i["tag"] for i in intents}:
            return jsonify(error="Intent tidak ditemukan."), 404
        if not pola or len(pola) > 100:
            return jsonify(error="Pola wajib diisi dan maksimal 100 karakter."), 400
        if not tokenisasi(pola):          # hanya kata henti (yang, di, ke, ...): tidak akan pernah cocok
            return jsonify(error="Pola tidak mengandung kata yang bermakna."), 400
        baku = normalisasi(pola)
        for item in intents_aktif():
            if any(normalisasi(p) == baku for p in item["patterns"]):
                return jsonify(error=f"Pola sudah ada di intent '{item['tag']}'."), 409
        return jsonify(id=simpan_pola_tambahan(app.config["DATABASE"], tag, pola)), 201

    @app.delete("/api/admin/pola/<int:pola_id>")
    def admin_hapus_pola(pola_id):
        if not admin_diizinkan():
            return jsonify(error="Akses admin ditolak."), 401
        if not hapus_pola_tambahan(app.config["DATABASE"], pola_id):
            return jsonify(error="Pola tidak ditemukan."), 404
        return jsonify(id=pola_id)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", application="CurryCoach", theme=theme_id)

    return app


app = create_app()
TEMA = muat_tema()
INTENTS = TEMA["intents"]
FALLBACK = TEMA["fallback"]
THRESHOLD = float(app.config["THRESHOLD"])


def cari_intent(pesan: str):
    """Wrapper kompatibilitas untuk pengujian dan pemanggil versi lama."""
    return _cari_intent(pesan, INTENTS, THRESHOLD)


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
