# PROGRES CURRYCOACH 2.0

Catatan ini diperbarui pada 26 November 2026. Deployment publik sengaja ditunda, jadi tidak ada URL produksi yang diklaim sudah aktif.

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
- Tabel identitas dan sesi Telegram ditambahkan:
  - `telegram_users` memetakan `telegram_id` ke `active_session_id` beserta username/nama.
  - `chat_sessions` menyimpan semua sesi milik satu user beserta label dan waktu pakai.
  - Fungsi baru: `sesi_aktif_telegram`, `daftar_sesi_telegram`, `info_sesi_aktif`, `sesi_baru_telegram`, `pilih_sesi_telegram`.
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
  - endpoint baru `GET /api/laporan/<telegram_id>` (dilindungi `ADMIN_KEY`);
  - `POST /api/chat` kini menerima `session_id` dan `simpan_riwayat` opsional agar bot Telegram bisa memakai sesi sendiri tanpa pesan dobel.
- Pertanyaan di luar topik masih jadi fallback: "siapa presiden indonesia", "resep nasi goreng", "cuaca hari ini".

### 2.4 Bot Telegram

`telegram_bot.py` sekarang memiliki:

- `/start` — daftar perintah lengkap.
- `/tanya` — memakai mesin Flask yang sama lewat `/api/chat`.
- `/latihan [filter]` — membaca katalog dari database, misalnya `/latihan pemula tanpa alat kaki`.
- `/catat` — alur tiga langkah: pilih nomor latihan, isi durasi, isi tembakan masuk; ada juga format cepat `/catat <id> <menit> <tembakan>`.
- `/laporan` — ringkasan 7 hari dan saran.
- `/lapangan` — lokasi Telegram → Overpass API → cache 24 jam.
- `/session` — melihat daftar sesi, jumlah pesan, dan sesi aktif.
- `/session <nomor>` — berpindah ke sesi lama milik user yang sama.
- `/session baru` atau `/reset` — membuat sesi baru; sesi lama tetap tersimpan.
- `/user` — menampilkan ID Telegram, username, nama, dan sesi aktif.
- `/riwayat` — menampilkan 5 pesan terakhir pada sesi aktif.
- `kirim_pengingat()` — mengingatkan pengguna yang belum berlatih selama 2 hari; dipanggil sekali per hari saat polling.
- Setiap user Telegram dibedakan oleh `telegram_id`; masing-masing mendapat session_id UUID tersendiri di database.
- Semua pesan bot Telegram (perintah, balasan, lokasi, dan pengingat) disimpan ke tabel `messages` pada session_id aktif. Untuk `/tanya`, Flask hanya menghitung jawaban (`simpan_riwayat: false`) dan bot yang menyimpan pasangan pesan agar tidak dobel.

### 2.5 Analitik dan rekomendasi

- `analytics/laporan.py` memakai pandas untuk total sesi, total menit, rata-rata durasi, tembakan masuk, dan kategori teratas.
- `analytics/rekomendasi.py` memberi saran berbasis aturan yang bisa dijelaskan, misalnya menambah frekuensi atau durasi.
- Keduanya dipakai oleh `/laporan` di Telegram dan `/api/laporan/<id>` di web.

### 2.6 Pengujian

- `tests/test_integrations.py` berisi 7 tes bot offline (tanpa jaringan dan tanpa token asli), termasuk sesi baru, ganti sesi, identitas user, dan penyimpanan pesan user+bot.
- `tests/test_data.py` berisi 6 tes untuk JSON scraping, deduplikasi, format wger, TF-IDF, sesi Telegram, dan analitik.
- `tests/test_backend.py` ditambah 1 tes untuk endpoint `/api/latihan` dan `/api/laporan/<id>`.
- `requirements.txt` ditambah `pandas` dan `scikit-learn`.
- Hasil akhir: **202 test lolos** dan **evaluasi 37/37 benar**.
- Perintah:
  - `.venv\Scripts\python.exe -m pytest -q`
  - `.venv\Scripts\python.exe evaluate.py`

### 2.7 Tahap lanjut: tampilan web, kelola data, dan skrip otomatis

- Halaman `/katalog`: katalog latihan dengan filter level, alat, dan otot (data dari database).
- Halaman `/progres`: dashboard latihan pribadi (kartu ringkasan, grafik SVG 14 hari, porsi kategori, saran, sesi terbaru). Dibuka lewat tautan bertoken dari perintah bot `/dashboard`. Token ditandatangani dengan `SECRET_KEY` dan berlaku 24 jam (`chatbot/tautan.py`).
- Halaman `/admin/kelola`: CRUD latihan (validasi, hapus ditolak 409 jika sudah dipakai sesi) dan pola tambahan chatbot dari pertanyaan yang belum dikenali (tabel `pola_tambahan`, berlaku langsung tanpa restart).
- OpenStreetMap: hasil sekarang diurutkan dari yang terdekat (jarak haversine) dan radius diperbesar bertahap 5, 10, 15 km.
- `scripts/update_data.py` (scraping, impor referensi, dan impor wger dalam satu perintah; ada `--dry-run` dan `--offline`) dan `scripts/rekap_harian.py` (rekap harian ke CSV).
- Pengujian: 248 kasus lolos (`tests/test_tahap_lanjut.py` menambah 46 kasus). Evaluasi intent tetap 37/37.

## 3. Yang belum dikerjakan

1. Deployment publik: sengaja ditunda sampai tanggalnya ditentukan. `render.yaml` dan `DEPLOYMENT.md` hanya persiapan.
2. Commit perubahan ke Git: semua perubahan masih berupa file kerja.
3. Pengujian langsung bot Telegram: database lokal belum memuat pengguna Telegram, jadi alur dengan token asli belum terbukti. Uji manual `/start`, `/tanya`, `/catat`, `/laporan`, `/dashboard`, dan kirim lokasi.
4. Cakupan OpenStreetMap: pencarian di sekitar koordinat Yogyakarta sebelumnya mengembalikan 0 lapangan. Data OSM di sana mungkin belum lengkap. Uji dengan beberapa lokasi dan siapkan penjelasan untuk dosen.
5. `TEMPLATE-LAPORAN-AKHIR.md` masih berisi placeholder `[ISI ...]`.
6. Tabel di dokumen Final Description Web App masih berupa gambar dan perlu diubah ke tabel teks.
7. Final Description Scripting perlu menyebut wger, pengingat, `/dashboard`, `update_data.py`, dan meluruskan bahwa catatan harian bukan scraping.
8. Penjadwalan otomatis `rekap_harian.py` dan `kirim_pengingat` belum dipasang di Task Scheduler.

## 4. Catatan sebelum mengumpulkan

- Jangan memasukkan `.env`, `.venv`, `instance/*.sqlite3`, dan `data/osm_cache.json`.
- Hasil scraping di `data/references/` sengaja tidak lagi diabaikan Git agar bisa dijadikan bukti.
- Estimasi kemajuan terbaru sekitar 92 dari 100 poin; sisanya hanya deployment publik.
