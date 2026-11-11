"""Aplikasi CurryCoach: edukasi basket pemula dengan Flask dan SQLite."""
from __future__ import annotations
import hmac
import os
import random
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session
from chatbot.database import (
    ambil_riwayat, hapus_riwayat, init_db, simpan_pesan, statistik,
)
from chatbot.engine import (
    DEFAULT_THRESHOLD, cari_intent as _cari_intent, cari_intent_detail,
    muat_tema, normalisasi,
)

BASE = Path(__file__).resolve().parent
MAKS_PANJANG = 300
KUNCI_WAJIB = ["id", "name", "bot_name", "avatar", "color", "description",
               "greeting", "suggestions", "fallback", "intents"]


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
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-this-secret"),
        DATABASE=os.getenv("DATABASE", str(BASE / "instance" / "currycoach.sqlite3")),
        THRESHOLD=float(os.getenv("THRESHOLD", str(DEFAULT_THRESHOLD))),
        ADMIN_KEY=os.getenv("ADMIN_KEY", ""),
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

    def session_id() -> str:
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        return session["session_id"]

    def isi_placeholder(teks: str) -> str:
        return teks.replace("{nama_bot}", tema["bot_name"])

    def proses_pesan(pesan: str, explain: bool = False) -> dict:
        terbaik, kandidat = cari_intent_detail(
            pesan, intents, float(app.config["THRESHOLD"])
        )
        if terbaik is None:
            intent_tag = "fallback"
            jawaban = isi_placeholder(random.choice(fallback))
            score = round(kandidat[0]["score"], 4) if kandidat else 0.0
        else:
            intent_tag = terbaik["intent"]["tag"]
            jawaban = isi_placeholder(random.choice(terbaik["intent"]["responses"]))
            score = round(terbaik["score"], 4)

        sid = session_id()
        simpan_pesan(app.config["DATABASE"], sid, theme_id, "user", pesan)
        simpan_pesan(app.config["DATABASE"], sid, theme_id, "bot", jawaban,
                     intent=intent_tag, score=score)
        hasil = {"reply": jawaban, "intent": intent_tag, "score": score}
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
        return jsonify(proses_pesan(pesan))

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
