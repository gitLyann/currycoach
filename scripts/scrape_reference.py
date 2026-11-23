"""Scraper referensi edukasi: cek robots.txt, jeda, dan simpan metadata/teks."""
from __future__ import annotations
import argparse
import csv
import json
import time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "references"
USER_AGENT = "CurryCoachEducationalBot/1.0 (+student project; respectful crawler)"


def scrape(url: str, delay: float = 2.0) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL harus menggunakan http atau https.")
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robot = urllib.robotparser.RobotFileParser()
    robot.set_url(robots_url)
    try:
        robot.read()
    except Exception as exc:
        raise RuntimeError(f"Tidak dapat memeriksa robots.txt ({robots_url}): {exc}") from exc
    if not robot.can_fetch(USER_AGENT, url):
        raise PermissionError("URL tidak diizinkan oleh robots.txt untuk crawler ini.")
    time.sleep(max(1.0, min(float(delay), 10.0)))
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        raise ValueError(f"Konten bukan HTML: {content_type}")
    soup = BeautifulSoup(response.text, "html.parser")
    for node in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        node.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else parsed.netloc
    paragraphs = [
        p.get_text(" ", strip=True) for p in soup.find_all(["p", "li"])
        if len(p.get_text(" ", strip=True)) >= 60
    ]
    record = {
        "source_url": url,
        "domain": parsed.netloc,
        "title": title,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "paragraphs": paragraphs[:80],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUT_DIR / f"reference_{stamp}.json"
    csv_path = OUT_DIR / f"reference_{stamp}.csv"
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["source_url", "title", "paragraph"])
        writer.writeheader()
        for paragraph in paragraphs:
            writer.writerow({"source_url": url, "title": title, "paragraph": paragraph})
    return {"title": title, "paragraph_count": len(paragraphs),
            "json_file": str(json_path.relative_to(ROOT)),
            "csv_file": str(csv_path.relative_to(ROOT))}


def main():
    parser = argparse.ArgumentParser(description="Ambil referensi HTML yang diizinkan robots.txt.")
    parser.add_argument("url", help="URL halaman referensi yang akan diambil")
    parser.add_argument("--delay", type=float, default=2.0, help="Jeda sebelum request (default 2 detik)")
    args = parser.parse_args()
    result = scrape(args.url, args.delay)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
