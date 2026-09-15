"""
Configuración central del bot (variables de entorno tipadas).

IMPORTANTE: este paquete (``src/config/``) es el que resuelve Python para
``from src.config import ...``. El antiguo módulo ``bot/src/config.py`` fue
eliminado porque quedaba "sombreado" por este paquete (nunca se ejecutaba)
y podía confundir al modificar variables.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Raíz del proyecto bot/  (src/config/__init__.py -> src/config -> src -> bot)
BASE_DIR = Path(__file__).resolve().parents[2]

# Cargar .env explícitamente desde la raíz del bot
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
load_dotenv(override=False)


# ─────────────────────────────────────────────────────────────────
# Helpers de parseo (evita el bug clásico: "0" es truthy)
# ─────────────────────────────────────────────────────────────────
def _as_bool(value, default=False):
    """Convierte 1/true/yes/si/on en True. Cualquier otro valor -> default."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "si", "sí", "on")


def _as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_symbol_list(*values):
    """Une strings separados por coma/; en una lista de símbolos únicos en mayúsculas."""
    symbols = []
    for value in values:
        if not value:
            continue
        for chunk in str(value).replace(";", ",").split(","):
            symbol = chunk.strip().upper()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return symbols


def _resolve_path(raw_value, default_path):
    """Devuelve un Path absoluto, resolviendo rutas relativas contra BASE_DIR."""
    raw = raw_value if raw_value else str(default_path)
    path = Path(raw)
    return path if path.is_absolute() else (BASE_DIR / path)


# ─────────────────────────────────────────────────────────────────
# Directorios y archivos de datos
# ─────────────────────────────────────────────────────────────────
DATA_DIR = _resolve_path(os.getenv("DATA_DIR"), BASE_DIR / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_FILE = _resolve_path(os.getenv("TOKEN_FILE"), DATA_DIR / "session_token.json")
QUOTES_FILE = _resolve_path(os.getenv("QUOTES_FILE"), DATA_DIR / "cotizaciones.json")
REPORT_FILE = _resolve_path(os.getenv("REPORT_FILE"), DATA_DIR / "informe_inversion.md")
# Archivo "legacy" que ya generaba el cliente en la raíz del bot (compatibilidad)
QUOTES_LATEST_FILE = _resolve_path(os.getenv("QUOTES_LATEST_FILE"), BASE_DIR / "quotes_latest.json")
DATA_FILE = _resolve_path(os.getenv("DATA_FILE"), DATA_DIR / "data.json")


# ─────────────────────────────────────────────────────────────────
# Mercosur Casa de Bolsa
# ─────────────────────────────────────────────────────────────────
MERCOSUR_BASE_URL = os.getenv("MERCOSUR_BASE_URL", "https://cm.mercosur.com.ve").rstrip("/")
MERCOSUR_LOGIN_URL = os.getenv("MERCOSUR_LOGIN_URL", f"{MERCOSUR_BASE_URL}/portal/login")
MERCOSUR_COTIZACIONES_URL = os.getenv(
    "MERCOSUR_COTIZACIONES_URL", f"{MERCOSUR_BASE_URL}/portal/mercado/dashboard/cotizaciones"
)
MERCOSUR_SALDOS_URL = os.getenv("MERCOSUR_SALDOS_URL", f"{MERCOSUR_BASE_URL}/portal/saldos")
MERCOSUR_MOVIMIENTOS_URL = os.getenv("MERCOSUR_MOVIMIENTOS_URL", f"{MERCOSUR_BASE_URL}/portal/movimientos")
MERCOSUR_COMPRA_VENTA_URL = os.getenv("MERCOSUR_COMPRA_VENTA_URL", f"{MERCOSUR_BASE_URL}/portal/compra-venta")
MERCOSUR_ORDENES_URL = os.getenv("MERCOSUR_ORDENES_URL", f"{MERCOSUR_BASE_URL}/portal/ordenes")
MERCOSUR_TRANSFERENCIAS_URL = os.getenv("MERCOSUR_TRANSFERENCIAS_URL", f"{MERCOSUR_BASE_URL}/portal/transferencias")
MERCOSUR_PERFIL_URL = os.getenv("MERCOSUR_PERFIL_URL", f"{MERCOSUR_BASE_URL}/portal/perfil")
MERCOSUR_LOGOUT_URL = os.getenv("MERCOSUR_LOGOUT_URL", f"{MERCOSUR_BASE_URL}/portal/logout")

MERCOSUR_EMAIL = os.getenv("MERCOSUR_EMAIL") or os.getenv("MERCOSUR_USER", "")
MERCOSUR_PASSWORD = os.getenv("MERCOSUR_PASSWORD", "")
MERCOSUR_CLAVE_OPERACIONES = os.getenv("MERCOSUR_CLAVE_OPERACIONES", os.getenv("MERCOSUR_PIN", ""))

# True = envío real de órdenes a Mercosur, False = modo simulación/recomendación
AUTO_EXECUTE_ORDERS = _as_bool(os.getenv("AUTO_EXECUTE_ORDERS"), False)


# ─────────────────────────────────────────────────────────────────
# BNC en Línea (Selenium)
# ─────────────────────────────────────────────────────────────────
BNC_URL = os.getenv("BNC_URL", "https://personas.bncenlinea.com/")
BNC_TARJETA = os.getenv("BNC_TARJETA", "")
BNC_CEDULA = os.getenv("BNC_CEDULA", "")
BNC_PASSWORD = os.getenv("BNC_PASSWORD", "")
FETCH_BNC_BALANCE = _as_bool(os.getenv("FETCH_BNC_BALANCE"), False)
BNC_HEADLESS = _as_bool(os.getenv("BNC_HEADLESS"), True)


# ─────────────────────────────────────────────────────────────────
# Inteligencia Artificial (Ollama local), red y noticias
# ─────────────────────────────────────────────────────────────────
USE_AI = _as_bool(os.getenv("USE_AI"), True)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Red / timeouts
HTTP_TIMEOUT = _as_int(os.getenv("HTTP_TIMEOUT", os.getenv("TIMEOUT", "15")), 15)
TIMEOUT = HTTP_TIMEOUT
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
MERCOSUR_HEADLESS = _as_bool(os.getenv("MERCOSUR_HEADLESS"), True)

# Símbolos excluidos de recomendaciones y listados (ej. EXCLUDE_SYMBOL=BVL)
EXCLUDE_SYMBOLS_RAW = os.getenv("EXCLUDE_SYMBOL") or os.getenv("EXCLUDE_SYMBOLS") or ""
EXCLUDE_SYMBOL = EXCLUDE_SYMBOLS_RAW
EXCLUDE_SYMBOLS = _as_symbol_list(EXCLUDE_SYMBOLS_RAW)

# Fuentes RSS de noticias financieras (Venezuela)
DEFAULT_NEWS_FEEDS = [
    {"name": "Finanzas Digital", "url": "https://www.finanzasdigital.com/feed/"},
    {
        "name": "Google News - Bolsa de Valores de Caracas",
        "url": "https://news.google.com/rss/search?q=Bolsa+de+Valores+de+Caracas+Venezuela&hl=es-419&gl=VE&ceid=VE:es-419",
    },
    {
        "name": "Google News - Economía Venezuela",
        "url": "https://news.google.com/rss/search?q=Economia+Venezuela+empresas&hl=es-419&gl=VE&ceid=VE:es-419",
    },
]


def _build_news_feeds():
    """NEWS_FEEDS del .env (URLs separadas por coma) o el listado por defecto."""
    raw = (os.getenv("NEWS_FEEDS") or "").strip()
    if not raw:
        return [dict(feed) for feed in DEFAULT_NEWS_FEEDS]

    feeds = []
    for url in (chunk.strip() for chunk in raw.replace(";", ",").split(",")):
        if url.startswith("http"):
            feeds.append({"name": f"RSS {len(feeds) + 1}", "url": url})
    return feeds or [dict(feed) for feed in DEFAULT_NEWS_FEEDS]


NEWS_FEEDS = _build_news_feeds()

