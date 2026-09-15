"""Configuración de logging: consola + archivo rotativo (data/bot.log).

Uso desde main.py / CLI:
    from src.logging_setup import setup_logging
    setup_logging()                      # nivel de LOG_LEVEL o INFO
    setup_logging(verbose=True, quiet=True)
"""
import logging
from logging.handlers import RotatingFileHandler

try:
    from src.config import LOG_BACKUPS, LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES
except Exception:  # pragma: no cover
    LOG_FILE, LOG_LEVEL, LOG_MAX_BYTES, LOG_BACKUPS = None, "INFO", 1_000_000, 3

_configured = False


def setup_logging(level=None, quiet=False, verbose=False):
    """Configura el logger raíz. Idempotente: no duplica handlers."""
    global _configured
    logger = logging.getLogger()

    if _configured:
        return logger

    if verbose:
        resolved = "DEBUG"
    else:
        resolved = str(level or LOG_LEVEL or "INFO").upper()
    numeric_level = getattr(logging, resolved, logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Consola (se silencia en modo --quiet)
    if not quiet:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(numeric_level)
        logger.addHandler(stream_handler)

    # Archivo con rotación
    if LOG_FILE:
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(numeric_level)
            logger.addHandler(file_handler)
        except Exception:
            pass

    logger.setLevel(logging.DEBUG)
    _configured = True
    return logger


def get_logger(name=None):
    """Atajo para obtener un logger y garantizar que la configuración existe."""
    if not _configured:
        setup_logging()
    return logging.getLogger(name)
