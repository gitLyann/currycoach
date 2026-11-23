# PROGRES CURRYCOACH 2.0

Catatan ini ditulis pada 23 November 2026. Deployment publik sengaja ditunda, jadi tidak ada URL produksi yang diklaim sudah aktif.

## 1. Keadaan awal sebelum pekerjaan ini

- Test dasar: 188 kasus lolos.
- Evaluasi intent: 37/37 benar (100%).
- Bot Telegram, API, scraping, TF-IDF, dan analitik sudah ada sebagian sebagai kode, tetapi belum terhubung dan belum dibuktikan dengan data nyata.
- Laporan kemajuan lama menyebut angka 22% dan menganggap scraping/API/bot belum ada; angka itu sudah tidak menggambarkan worktree saat ini.

## 2. Yang sudah dikerjakan

### 2.1 Scraping nyata

- Memperbaiki `scripts/scrape_reference.py`:
  - `robots.txt` kini diambil dengan User-Agent proyek, bukan User-Agent default `urllib` yang ditolak Wikipedia (403).
  - Nama file hasil scraping memakai mikrodetik agar proses paralel tidak menimpa file.
- Sumber yang dipakai (halaman artikel diizinkan oleh `robots.txt` Wikipedia):
  - `https://en.wikipedia.org/wiki/Basketball`
  - `https://en.wikipedia.org/wiki/Dribble`
  - `https://en.wikipedia.org/wiki/Free_throw`
- Perintah:
  - `python scripts/scrape_reference.py "URL" --delay 2`
- Hasil: 3 artikel, 349 paragraf terbaca, 181 paragraf disimpan (skrip membatasi 80 paragraf per artikel).
- Bukti mentah: `data/references/reference_*.json` dan `data/references/reference_*.csv`.
- File pendukung lain yang sebelumnya disalahartikan sebagai hasil scraping:
  - `evaluasi/currycoach.csv` adalah data uji akurasi, bukan hasil scraping.
  - `data/osm_cache.json` adalah cache API Overpass, bukan scraping.
  - `currycoach.json` adalah basis pengetahuan rules, bukan korpus scraping.

### 2.2 Database dan import data

- `chatbot/database.py` sekarang memiliki tabel:
  - `referensi` (paragraf hasil scraping, unik per URL + paragraf),
  - `exercises` (katalog latihan dari wger),
  - `workout_sessions` (catatan latihan per ID Telegram).
- Fungsi baru: `simpan_referensi`, `ambil_referensi`, `simpan_latihan`, `cari_latihan`, `ambil_latihan`, `simpan_sesi_latihan`, `ambil_sesi_latihan`, `data_sesi_latihan`, `pengguna_perlu_pengingat`.
- `config.py` menyatukan path database, direktori referensi, URL wger, dan variabel lingkungan bot.
- `scripts/import_data.py`:
  - membaca semua `data/references/*.json`,
  - mengambil 150 latihan dari API publik wger,
  - menyesuaikan format terbaru wger yang menyimpan nama/deskripsi di `translations`,
  - menyimpan snapshot ke `data/exercises_wger.json`,
  - mendukung `--offline` agar impor bisa diulang tanpa internet.
- Perintah: `python scripts/import_data.py --limit 150`.
- Isi database lokal saat ini: 181 paragraf referensi, 150 latihan, 51 di antaranya berlevel pemula tanpa alat.

### 2.3 TF-IDF dan retrieval di aplikasi

- `chatbot/tfidf.py` membangun korpus dari tabel `referensi`, dikelompokkan per artikel lalu dipotong menjadi potongan 3 paragraf agar skor kemiripan tidak terlalu encer.
- `chatbot/handlers.py` menerjemahkan kalimat menjadi filter latihan (level, alat, otot) dan format jawaban.
- `app.py`:
  - menjalankan TF-IDF sebelum fallback; contoh "bagaimana sejarah permainan basket?" kini dijawab dari Wikipedia dengan intent `referensi` dan skor 0,3565;
  - menambahkan rekomendasi latihan dari database saat intent `program_latihan` terdeteksi;
  - endpoint baru `GET /api/latihan` dengan filter `level`, `alat`, `otot`, `limit`;
  - endpoint baru `GET /api/laporan/<telegram_id>` (dilindungi `ADMIN_KEY`).
- Pertanyaan di luar topik masih jadi fallback: "siapa presiden indonesia", "resep nasi goreng", "cuaca hari ini".

### 2.4 Bot Telegram

`telegram_bot.py` sekarang memiliki:

- `/start` — daftar perintah lengkap.
- `/tanya` — memakai mesin Flask yang sama lewat `/api/chat`.
- `/latihan [filter]` — membaca katalog dari database, misalnya `/latihan pemula tanpa alat kaki`.
- `/catat` — alur tiga langkah: pilih nomor latihan, isi durasi, isi tembakan masuk; ada juga format cepat `/catat <id> <menit> <tembakan>`.
- `/laporan` — ringkasan 7 hari dan saran.
- `/lapangan` — lokasi Telegram → Overpass API → cache 24 jam.
- `kirim_pengingat()` — mengingatkan pengguna yang belum berlatih selama 2 hari; dipanggil sekali per hari saat polling.

### 2.5 Analitik dan rekomendasi

- `analytics/laporan.py` memakai pandas untuk total sesi, total menit, rata-rata durasi, tembakan masuk, dan kategori teratas.
- `analytics/rekomendasi.py` memberi saran berbasis aturan yang bisa dijelaskan, misalnya menambah frekuensi atau durasi.
- Keduanya dipakai oleh `/laporan` di Telegram dan `/api/laporan/<id>` di web.

### 2.6 Pengujian

- `tests/test_integrations.py` ditambah 4 tes bot offline (tanpa jaringan dan tanpa token asli).
- `tests/test_data.py` ditambah 5 tes untuk JSON scraping, deduplikasi, format wger, TF-IDF, dan analitik.
- `tests/test_backend.py` ditambah 1 tes untuk endpoint `/api/latihan` dan `/api/laporan/<id>`.
- `requirements.txt` ditambah `pandas` dan `scikit-learn`.
- Hasil akhir: **198 test lolos** dan **evaluasi 37/37 benar**.
- Perintah:
  - `.venv\Scripts\python.exe -m pytest -q`
  - `.venv\Scripts\python.exe evaluate.py`

## 3. Yang belum dikerjakan

1. Deployment publik — sengaja ditunda. `render.yaml` dan `DEPLOYMENT.md` hanya persiapan.
2. Upload/commit perubahan — semua perubahan di atas masih berupa file kerja, belum di-commit.
3. Tab web "Latihan Saya" dan "Katalog" — API sudah ada, tampilan belum.
4. Admin CRUD untuk intent dan latihan.
5. `TEMPLATE-LAPORAN-AKHIR.md` masih berisi placeholder `[ISI ...]`.
6. Tabel di dokumen Final Description Web App masih berupa gambar dan perlu diubah ke tabel teks.
7. Final Description Scripting perlu menyebut wger dan pengingat, serta meluruskan bahwa catatan harian bukan scraping.
8. Token Telegram di `.env` sudah ada, tetapi harus diuji langsung dengan BotFather dan perangkat Telegram. Jangan pernah membagikan nilainya.

## 4. Catatan sebelum mengumpulkan

- Jangan memasukkan `.env`, `.venv`, `instance/*.sqlite3`, dan `data/osm_cache.json`.
- Hasil scraping di `data/references/` sengaja tidak lagi diabaikan Git agar bisa dijadikan bukti.
- Angka persentase laporan lama perlu dihitung ulang karena sekarang sudah ada bukti scraping, API, bot, TF-IDF, dan analitik; hanya deployment yang belum.
