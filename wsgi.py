"""Entry point WSGI untuk server produksi."""
from app import create_app

app = create_app()
