"""Tes validasi offline untuk modul integrasi tahap 54%."""
import pytest
from services.osm import cari_lapangan
from scripts.scrape_reference import scrape


def test_osm_rejects_invalid_coordinates_without_network():
    with pytest.raises(ValueError):
        cari_lapangan(120, 200)


def test_scraper_rejects_non_http_url_without_network():
    with pytest.raises(ValueError):
        scrape("file:///etc/passwd")
