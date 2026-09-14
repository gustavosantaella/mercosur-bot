import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env en la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

# Directorio de salidas de datos
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Archivo de persistencia de token JWT
TOKEN_FILE = DATA_DIR / "session_token.json"

# Mercosur API Config
MERCOSUR_LOGIN_URL = os.getenv("MERCOSUR_LOGIN_URL", "https://cm.mercosur.com.ve/portal/login")
MERCOSUR_COTIZACIONES_URL = os.getenv("MERCOSUR_COTIZACIONES_URL", "https://cm.mercosur.com.ve/portal/mercado/dashboard/cotizaciones")
MERCOSUR_SALDOS_URL = os.getenv("MERCOSUR_SALDOS_URL", "https://cm.mercosur.com.ve/portal/saldos")
MERCOSUR_ORDENES_URL = os.getenv("MERCOSUR_ORDENES_URL", "https://cm.mercosur.com.ve/portal/ordenes")

MERCOSUR_EMAIL = os.getenv("MERCOSUR_EMAIL", "")
MERCOSUR_PASSWORD = os.getenv("MERCOSUR_PASSWORD", "")
MERCOSUR_CLAVE_OPERACIONES = os.getenv("MERCOSUR_CLAVE_OPERACIONES", os.getenv("MERCOSUR_PIN", ""))


# Control de Ejecución Automática de Órdenes (1 = Ejecución Real en Mercosur, 0 = Modo Simulación/Recomendación)
AUTO_EXECUTE_ORDERS = os.getenv("AUTO_EXECUTE_ORDERS", "0").strip() == "1"

# Configuración BNC en Línea (Web Scraping Selenium)

BNC_URL = os.getenv("BNC_URL", "https://personas.bncenlinea.com/")
BNC_TARJETA = os.getenv("BNC_TARJETA", "")
BNC_CEDULA = os.getenv("BNC_CEDULA", "")
BNC_PASSWORD = os.getenv("BNC_PASSWORD", "")
FETCH_BNC_BALANCE = os.getenv("FETCH_BNC_BALANCE", "0").strip() == "1"
BNC_HEADLESS = os.getenv("BNC_HEADLESS", "1").strip() == "1"

# Control de Habilitación de IA (1 = Activa, 0 = Inactiva)
USE_AI = os.getenv("USE_AI", "1").strip() == "1"

# Símbolos / Empresas a ignorar/excluir (separados por comas)
EXCLUDE_SYMBOLS_RAW = os.getenv("EXCLUDE_SYMBOL", "")
EXCLUDE_SYMBOLS = [s.strip().upper() for s in EXCLUDE_SYMBOLS_RAW.split(",") if s.strip()]

# Configuración de IA Local (Ollama)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# News Feed RSS URLs para noticias financieras de Venezuela (Fuentes 100% estables y activas)
NEWS_FEEDS = [
    {
        "name": "Finanzas Digital",
        "url": "https://www.finanzasdigital.com/feed/"
    },
    {
        "name": "Google News - Bolsa de Valores de Caracas",
        "url": "https://news.google.com/rss/search?q=Bolsa+de+Valores+de+Caracas+Venezuela&hl=es-419&gl=VE&ceid=VE:es-419"
    },
    {
        "name": "Google News - Economía Venezuela",
        "url": "https://news.google.com/rss/search?q=Economia+Venezuela+empresas&hl=es-419&gl=VE&ceid=VE:es-419"
    }
]
