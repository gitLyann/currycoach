# CurryCoach — Tahap 3: UI dan Admin Dashboard

CurryCoach adalah chatbot edukasi basket untuk pemula. Tahap ini memperbarui antarmuka chat dan menambahkan dashboard admin berbasis data SQLite, tanpa mengganti mesin chatbot maupun API pada Tahap 2.

## Identitas visual

- Warriors Blue: `#1D428A`
- Warriors Gold: `#FFC72C`
- Font antarmuka: DM Sans dan Outfit (Google Fonts; fallback sistem tetap tersedia)
- Layout responsif untuk desktop, tablet, dan ponsel.

## Instalasi dan menjalankan

```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "ganti-dengan-secret-random-yang-panjang"
$env:ADMIN_KEY = "ganti-dengan-kunci-admin-yang-kuat"
python app.py
```

Buka:
- Chat: `http://127.0.0.1:5000/`
- Admin: `http://127.0.0.1:5000/admin`

Jika `ADMIN_KEY` disetel, masukkan nilai yang sama pada halaman Admin Dashboard. Kunci hanya disimpan di `sessionStorage` browser dan dikirim melalui header `X-Admin-Key`; jangan gunakan halaman ini melalui koneksi HTTP publik tanpa HTTPS.

## Fitur UI Tahap 3

- Chat UI baru dengan palet Warriors Blue dan Warriors Gold.
- Layout responsif desktop dan mobile.
- Riwayat percakapan dimuat dari `/api/history/currycoach`.
- Hapus riwayat sesi melalui `DELETE /api/history/currycoach`.
- Quick suggestions dari `currycoach.json`.
- Explain Mode menggunakan `/api/explain` untuk menampilkan kandidat intent dan skor.
- Pesan pengguna dan balasan dirender menggunakan `textContent` untuk mengurangi risiko XSS.
- Admin Dashboard menggunakan `/api/stats/currycoach`, dengan kartu metrik, grafik batang distribusi intent, ringkasan recognized/fallback, dan tabel pertanyaan yang belum dikenali.

## Endpoint backend

Seluruh endpoint Tahap 2 dipertahankan: `/chat`, `/api/chat`, `/api/explain`, `/api/history/<theme>`, `/api/stats/<theme>`, `/api/themes`, dan `/api/health`. Halaman baru `/admin` hanya menyajikan antarmuka; proteksi data statistik tetap berada pada endpoint API.

## Pengujian

```powershell
pytest -v
```

Database lokal dibuat otomatis di `instance/currycoach.sqlite3`. Database tidak disertakan dalam arsip ZIP.

## Catatan

- Grafik dibuat dengan HTML/CSS dan JavaScript tanpa dependensi chart eksternal.
- Font Google Fonts memerlukan koneksi internet; fallback font sistem akan digunakan jika tidak tersedia.
- Untuk deployment, wajib gunakan `SECRET_KEY` dan `ADMIN_KEY` yang kuat, HTTPS, serta server WSGI produksi. Jangan aktifkan Flask debug mode.
