import socket
import requests
import feedparser
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from src.config import NEWS_FEEDS

# Connectivity check target — lightweight, no payload
_CONNECTIVITY_HOST = "8.8.8.8"
_CONNECTIVITY_PORT = 53
_CONNECTIVITY_TIMEOUT = 3


def _has_internet() -> bool:
    """Quick TCP probe to confirm internet connectivity before attempting RSS feeds."""
    try:
        socket.setdefaulttimeout(_CONNECTIVITY_TIMEOUT)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(
            (_CONNECTIVITY_HOST, _CONNECTIVITY_PORT))
        return True
    except (socket.timeout, OSError):
        return False


class NewsFetcher:
    """
    Extractor de noticias financieras y económicas nacionales de Venezuela.
    Utiliza headers de navegador real para evitar bloqueos anti-bot en medios locales.
    """

    def __init__(self, feeds: List[Dict[str, str]] = NEWS_FEEDS):
        self.feeds = feeds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7"
        })

    def fetch_latest_news(self, max_per_feed: int = 5) -> List[Dict[str, Any]]:
        """
        Obtiene noticias recientes desde los RSS configurados.
        Retorna lista vacía silenciosamente si no hay conectividad a internet.
        """
        # ── Connectivity pre-check ────────────────────────────────
        if not _has_internet():
            print("[Info] Sin acceso a internet — se omite la obtención de noticias.")
            return []

        all_news = []

        for feed_info in self.feeds:
            feed_name = feed_info["name"]
            url = feed_info["url"]

            try:
                response = self.session.get(url, timeout=10)
                parsed = feedparser.parse(
                    response.content if response.status_code == 200 else url
                )

                for entry in parsed.entries[:max_per_feed]:
                    summary_raw = entry.get("summary", "") or entry.get("description", "")
                    clean_summary = (
                        BeautifulSoup(summary_raw, "html.parser").get_text(strip=True)
                        if summary_raw else ""
                    )
                    all_news.append({
                        "fuente": feed_name,
                        "titulo": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "resumen": clean_summary[:300] + ("..." if len(clean_summary) > 300 else ""),
                        "fecha": entry.get("published", entry.get("updated", "Reciente"))
                    })

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.SSLError) as e:
                # Network-level failure — short, clean message; no traceback
                reason = type(e).__name__
                print(f"[Warning] {feed_name}: no disponible ({reason}).")
            except Exception as e:
                # Unexpected error — keep full message for debugging
                print(f"[Warning] Error inesperado al obtener noticias de {feed_name}: {e}")

        return all_news
