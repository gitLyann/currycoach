"""Pencocokan TF-IDF memakai korpus referensi hasil scraping."""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from chatbot.database import ambil_referensi
from chatbot.engine import normalisasi, tokenisasi


class MesinTFIDF:
    """Mesin kemiripan cosine TF-IDF untuk paragraf referensi basket."""

    def __init__(self, documents: list[str] | None = None,
                 sources: list[str] | None = None,
                 threshold: float = 0.22) -> None:
        self.threshold = float(threshold)
        self.documents = list(documents or [])
        self.sources = list(sources or self.documents)
        self.vectorizer = TfidfVectorizer(
            tokenizer=tokenisasi, lowercase=False, token_pattern=None,
        )
        self.matrix = None
        if self.documents:
            self.matrix = self.vectorizer.fit_transform(
                [normalisasi(doc) for doc in self.documents]
            )

    def cari(self, pertanyaan: str, top_n: int = 2) -> list[dict]:
        """Kembalikan referensi teratas yang melewati ambang batas."""
        if self.matrix is None or not str(pertanyaan or "").strip():
            return []
        vektor = self.vectorizer.transform([normalisasi(pertanyaan)])
        skor = cosine_similarity(vektor, self.matrix).ravel()
        if not len(skor):
            return []
        urutan = skor.argsort()[::-1][:max(1, min(int(top_n), len(skor)))]
        return [
            {
                "score": round(float(skor[i]), 4),
                "text": self.documents[i],
                "source": self.sources[i],
            }
            for i in urutan if float(skor[i]) >= self.threshold
        ]


def muat_mesin_dari_database(database: str, limit: int = 500,
                             threshold: float = 0.22) -> MesinTFIDF:
    """Bangun mesin TF-IDF dari tabel referensi yang sudah diisi."""
    baris = ambil_referensi(database, limit=limit)
    artikel: dict[str, list[str]] = {}
    for item in baris:
        artikel.setdefault(item["source_url"], []).append(item["paragraph"])
    dokumen, sumber = [], []
    for url, paragraf in artikel.items():
        for indeks in range(0, len(paragraf), 3):
            dokumen.append(" ".join(paragraf[indeks:indeks + 3]))
            sumber.append(url)
    return MesinTFIDF(
        documents=dokumen, sources=sumber, threshold=threshold,
    )
