# CurryCoach — Tahap 2: Backend Flask dan SQLite

Chatbot edukasi basket untuk pemula. Backend tahap ini mempertahankan mesin NLU dari Tahap 1 dan menambahkan API, sesi pengguna, riwayat SQLite, statistik, serta Explain Mode.

## Instalasi

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Atur variabel lingkungan (contoh PowerShell):
$env:SECRET_KEY = "ganti-dengan-secret-random-yang-panjang"
$env:ADMIN_KEY = "ganti-dengan-kunci-admin-yang-kuat"
python app.py
```

Buka `http://127.0.0.1:5000`. SQLite akan dibuat otomatis di `instance/currycoach.sqlite3`.

## Pengujian

```powershell
pytest -v
```

## Endpoint

| Method | Endpoint | Fungsi |
|---|---|---|
| GET | `/` | Halaman utama |
| GET | `/chat/currycoach` | Halaman chat berdasarkan tema |
| GET | `/api/themes` | Daftar tema |
| POST | `/chat` | Endpoint kompatibilitas versi lama |
| POST | `/api/chat` | Mengirim pesan dan menyimpan percakapan |
| POST | `/api/explain` | Chat dengan kandidat dan rincian skor intent |
| GET | `/api/history/currycoach` | Mengambil riwayat sesi aktif |
| DELETE | `/api/history/currycoach` | Menghapus riwayat sesi aktif |
| GET | `/api/stats/currycoach` | Statistik admin |
| GET | `/api/health` | Pemeriksaan status aplikasi |

Untuk endpoint statistik, kirim header `X-Admin-Key` yang sama dengan `ADMIN_KEY` pada konfigurasi. Jika `ADMIN_KEY` kosong, akses statistik terbuka untuk pengembangan lokal; atur kunci pada deployment. File `.env.example` hanya contoh nama variabel; Flask tidak otomatis membaca file `.env` tanpa library tambahan, sehingga atur variabel melalui environment seperti contoh PowerShell di atas.

## Bentuk data API

Kirim pesan dengan JSON `{"message":"halo","theme":"currycoach"}`. Respons berisi `reply`, `intent`, dan `score`. Explain Mode menambahkan `candidates` dan `threshold`.

## Keamanan dan batasan

- Query SQLite menggunakan parameter, bukan interpolasi input pengguna.
- Riwayat dipisahkan memakai ID sesi acak yang disimpan pada cookie Flask.
- Atur `SECRET_KEY` dan `ADMIN_KEY` yang kuat sebelum deployment.
- Jangan gunakan server development Flask untuk produksi.
- Database lokal tidak disertakan pada ZIP.
