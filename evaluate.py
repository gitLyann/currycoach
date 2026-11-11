"""Ukur akurasi CurryCoach dengan evaluasi/currycoach.csv (kolom: kalimat,intent).
Jalankan: python evaluate.py
"""
import csv
from collections import Counter
from pathlib import Path

from app import cari_intent

path = Path(__file__).parent / "evaluasi" / "currycoach.csv"
with open(path, encoding="utf-8") as f:
    data = [(r["kalimat"], r["intent"]) for r in csv.DictReader(f)]

hasil = []
for kalimat, harapan in data:
    intent = cari_intent(kalimat)
    tebakan = intent["tag"] if intent else "fallback"
    hasil.append((kalimat, harapan, tebakan))

benar = sum(1 for _, h, t in hasil if h == t)
print(f"Akurasi: {benar}/{len(data)} = {benar / len(data):.1%}\n")
total, tepat = Counter(h for _, h, _ in hasil), Counter(h for _, h, t in hasil if h == t)
for tag in sorted(total):
    print(f"{tag:18} {tepat[tag]}/{total[tag]}")
salah = [(k, h, t) for k, h, t in hasil if h != t]
if salah:
    print("\nKesalahan:")
    for k, h, t in salah:
        print(f'  "{k}": harapan {h}, tebakan {t}')
