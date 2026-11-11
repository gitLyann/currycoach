"""Evaluasi intent CurryCoach tanpa perlu menjalankan server Flask.

Jalankan dari folder proyek: python evaluate.py
Dataset: evaluasi/currycoach.csv (kolom kalimat,intent).
"""
import csv
from collections import Counter
from pathlib import Path

from chatbot.engine import cari_intent, muat_tema

BASE = Path(__file__).resolve().parent
DATASET = BASE / "evaluasi" / "currycoach.csv"


def main() -> None:
    tema = muat_tema(BASE / "currycoach.json")
    intents = tema["intents"]
    with DATASET.open(encoding="utf-8", newline="") as file:
        data = list(csv.DictReader(file))

    if not data:
        raise SystemExit("Dataset evaluasi kosong.")

    hasil = []
    for row in data:
        kalimat, harapan = row["kalimat"].strip(), row["intent"].strip()
        prediksi = cari_intent(kalimat, intents)
        tebakan = prediksi["tag"] if prediksi else "fallback"
        hasil.append((kalimat, harapan, tebakan))

    benar = sum(harapan == tebakan for _, harapan, tebakan in hasil)
    total = len(hasil)
    akurasi = benar / total
    jumlah_per_intent = Counter(harapan for _, harapan, _ in hasil)
    benar_per_intent = Counter(harapan for _, harapan, tebakan in hasil if harapan == tebakan)
    jumlah_fallback = jumlah_per_intent["fallback"]

    print("=" * 58)
    print("EVALUASI CHATBOT CURRYCOACH")
    print("=" * 58)
    print(f"Total data       : {total}")
    print(f"Prediksi benar   : {benar}")
    print(f"Prediksi salah   : {total - benar}")
    print(f"Akurasi          : {akurasi:.1%} ({benar}/{total})")
    print(f"Pertanyaan OOD   : {jumlah_fallback} (label fallback)")
    print("\nAkurasi per intent:")
    for tag in sorted(jumlah_per_intent):
        n = jumlah_per_intent[tag]
        print(f"- {tag:18} {benar_per_intent[tag]}/{n} ({benar_per_intent[tag] / n:.1%})")

    salah = [(kalimat, harapan, tebakan) for kalimat, harapan, tebakan in hasil
             if harapan != tebakan]
    if salah:
        print("\nPrediksi yang perlu diperiksa:")
        for kalimat, harapan, tebakan in salah:
            print(f'- "{kalimat}" | seharusnya: {harapan} | prediksi: {tebakan}')
    else:
        print("\nTidak ada kesalahan pada dataset ini.")


if __name__ == "__main__":
    main()
