"""Obtención de noticias financieras (RSS/Atom) con degradación elegante.

- Si no hay internet, retorna [] sin lanzar excepciones.
- Soporta feeds RSS (<item>) y Atom (<entry>), con o sin namespaces.
- Usa las fuentes definidas en src/config (NEWS_FEEDS del .env o las de defecto).
"""
import html
import re
import socket
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

try:
    from src.config import NEWS_FEEDS, HTTP_TIMEOUT
except Exception:  # pragma: no cover - fallback defensivo
    NEWS_FEEDS = [{"name": "Finanzas Digital", "url": "https://www.finanzasdigital.com/feed/"}]
    HTTP_TIMEOUT = 10

# Objetivo del chequeo de conectividad (liviano, sin payload)
_CONNECTIVITY_HOST = "8.8.8.8"
_CONNECTIVITY_PORT = 53
_CONNECTIVITY_TIMEOUT = 3

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")
_ENTITY_RE = re.compile(r"&([a-zA-Z][a-zA-Z0-9]{1,31});")
_ENTRY_TAGS = ("item", "entry")
_TEXT_TAGS = (
    "title", "link", "pubdate", "published", "updated",
    "description", "summary", "content",
)
# Entidades válidas en XML 1.0 (el resto hay que convertirlas o eliminarlas)
_XML_SAFE_ENTITIES = ("amp", "lt", "gt", "quot", "apos")


def _decode_payload(payload: bytes) -> str:
    """Decodifica el feed probando UTF-8 y, si falla, Latin-1 (común en medios locales)."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return payload.decode(encoding)
        except (UnicodeDecodeError, AttributeError):
            continue
    return str(payload)


def _sanitize_entities(text: str) -> str:
    """Convierte entidades HTML no declaradas (&oacute;, &nbsp;) para que XML las acepte.

    Muchos feeds locales incluyen entidades HTML dentro del texto; sin esta limpieza
    ElementTree falla con ParseError y se perdía el feed completo.
    """
    def _replace(match):
        name = match.group(1)
        if name in _XML_SAFE_ENTITIES:
            return match.group(0)
        decoded = html.unescape(f"&{name};")
        return "" if decoded == f"&{name};" else decoded

    return _ENTITY_RE.sub(_replace, text)


def _has_internet() -> bool:
    """Verifica si hay conexión a Internet resolviendo contra Google DNS."""
    original_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(_CONNECTIVITY_TIMEOUT)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((_CONNECTIVITY_HOST, _CONNECTIVITY_PORT))
        return True
    except Exception:
        return False
    finally:
        socket.setdefaulttimeout(original_timeout)


def _clean_text(raw: Any) -> str:
    """Quita HTML/entidades y normaliza espacios de un texto de RSS."""
    if raw is None:
        return ""
    text = _TAG_RE.sub(" ", str(raw))
    text = html.unescape(text)
    return _SPACE_RE.sub(" ", text).strip()


class NewsFetcher:
    """Extractor de noticias financieras/económicas para el mercado venezolano."""

    def __init__(self, feeds: Optional[List[Dict[str, str]]] = None, timeout: Optional[int] = None,
                 max_per_feed: int = 5):
        # feeds=None -> fuentes del config; feeds=[] -> sin fuentes (modo explícito)
        source_feeds = [dict(feed) for feed in NEWS_FEEDS] if feeds is None else list(feeds)
        self.feeds = source_feeds
        self.timeout = timeout or HTTP_TIMEOUT
        self.max_per_feed = max_per_feed

    # ── internos ────────────────────────────────────────────────
    @staticmethod
    def _normalize_feeds(feeds) -> List[Tuple[str, str]]:
        """Acepta dicts {"name","url"}, tuplas (name, url) o strings URL."""
        normalized = []
        for feed in feeds or []:
            if isinstance(feed, dict):
                name = feed.get("name") or "Fuente Desconocida"
                url = feed.get("url") or ""
            elif isinstance(feed, (list, tuple)) and len(feed) >= 2:
                name, url = str(feed[0]), str(feed[1])
            elif isinstance(feed, str):
                name, url = feed, feed
            else:
                continue
            url = str(url).strip()
            if url.startswith("http"):
                normalized.append((name, url))
        return normalized

    @staticmethod
    def _parse_feed(payload: bytes, feed_name: str, limit: int) -> List[Dict[str, Any]]:
        """Extrae titulares de un feed RSS o Atom (con o sin namespaces)."""
        news: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(_sanitize_entities(_decode_payload(payload)))
        except ET.ParseError:
            return news

        for entry in root.iter():
            tag = entry.tag.split("}")[-1].lower()
            if tag not in _ENTRY_TAGS:
                continue

            fields: Dict[str, str] = {}
            for child in entry:
                key = child.tag.split("}")[-1].lower()
                if key not in _TEXT_TAGS or key in fields:
                    continue
                if key == "link" and not (child.text or "").strip():
                    fields[key] = child.get("href", "") or ""
                else:
                    fields[key] = child.text or ""

            title = _clean_text(fields.get("title"))
            if not title:
                continue

            summary = _clean_text(
                fields.get("summary") or fields.get("description") or fields.get("content")
            )
            if len(summary) > 300:
                summary = summary[:300] + "..."

            news.append({
                "source": feed_name,
                "title": title,
                "link": (fields.get("link") or "").strip(),
                "pub_date": (fields.get("pubdate") or fields.get("published")
                             or fields.get("updated") or "").strip(),
                "summary": summary,
            })
            if len(news) >= limit:
                break

        return news

    # ── API pública ─────────────────────────────────────────────
    def fetch_latest_news(self, max_per_feed: Optional[int] = None) -> List[Dict[str, Any]]:
        """Devuelve titulares recientes. Lista vacía si no hay internet o fallan los feeds."""
        limit = max_per_feed or self.max_per_feed
        if not _has_internet():
            return []

        all_news: List[Dict[str, Any]] = []
        for feed_name, feed_url in self._normalize_feeds(self.feeds):
            try:
                request = urllib.request.Request(feed_url, headers={
                    "User-Agent": _USER_AGENT,
                    "Accept": "application/rss+xml, application/xml, text/xml, */*",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                })
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = response.read()
                all_news.extend(self._parse_feed(payload, feed_name, limit))
            except Exception:
                # Feed caído / bloqueado / timeout: se ignora y se continúa
                continue

        return all_news

