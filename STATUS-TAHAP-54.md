# Status Integrasi CurryCoach

Dokumen ini dahulu mencatat target tahap 54%. Target tersebut sudah terlampaui untuk sisi scripting, kecuali deployment publik yang sengaja ditunda sesuai permintaan.

Ringkasan terkini:

- Scraping Wikipedia sudah dijalankan; hasil ada di `data/references/`.
- API wger sudah diimpor ke tabel `exercises`; snapshot ada di `data/exercises_wger.json`.
- Bot Telegram memiliki `/start`, `/tanya`, `/latihan`, `/catat`, `/laporan`, `/lapangan`, pengingat, `/session`, `/user`, dan `/riwayat`.
- Identitas Telegram, sesi per user, dan semua pesan bot tersimpan di SQLite.
- TF-IDF, analitik pandas, dan rekomendasi sudah terhubung ke aplikasi.
- Pengujian: 202 test lolos dan evaluasi 37/37 benar.
- Deployment publik belum dilakukan dan belum diklaim selesai.

Rincian lengkap ada di `PROGRES.md`.
