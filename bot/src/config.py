import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas de archivos
TOKEN_FILE = BASE_DIR / "data" / "token.json"
COTIZACIONES_FILE = BASE_DIR / "data" / "cotizaciones.json"
REPORT_FILE = BASE_DIR / "data" / "informe_inversion.md"

# Credenciales Mercosur
MERCOSUR_EMAIL = os.getenv("MERCOSUR_EMAIL", "")
MERCOSUR_PASSWORD = os.getenv("MERCOSUR_PASSWORD", "")
MERCOSUR_CLAVE_OPERACIONES = os.getenv("MERCOSUR_CLAVE_OPERACIONES", "")

# Ollama / AI Config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
