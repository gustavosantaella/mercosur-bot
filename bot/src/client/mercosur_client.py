import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor

import requests
import urllib3
from dotenv import load_dotenv

try:
    from src.config import (
        EXCLUDE_SYMBOLS,
        HTTP_TIMEOUT,
        MERCOSUR_BASE_URL,
        QUOTES_FILE,
        QUOTES_LATEST_FILE,
    )
except Exception:  # pragma: no cover - permite importar el módulo de forma aislada
    EXCLUDE_SYMBOLS = []
    HTTP_TIMEOUT = 8
    MERCOSUR_BASE_URL = "https://cm.mercosur.com.ve"
    QUOTES_FILE = QUOTES_LATEST_FILE = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

DNS_SERVERS = ["8.8.8.8", "1.1.1.1", "200.44.32.12", "200.44.32.13", "9.9.9.9"]

def get_custom_dns_ip(host):
    try:
        import dns.resolver
        for dns_ip in DNS_SERVERS:
            try:
                resolver = dns.resolver.Resolver(configure=False)
                resolver.nameservers = [dns_ip]
                resolver.timeout = 1
                resolver.lifetime = 1
                answers = resolver.resolve(host, 'A')
                for rdata in answers:
                    return str(rdata)
            except Exception:
                continue
    except ImportError:
        pass
    return socket.gethostbyname(host)

_original_getaddrinfo = socket.getaddrinfo

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if "mercosur.com.ve" in host:
        ip = get_custom_dns_ip(host)
        return _original_getaddrinfo(ip, port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo

class MercosurClient:
    def __init__(self):
        self.base_url = MERCOSUR_BASE_URL
        self.url_quotes = f"{self.base_url}/portal/mercado/dashboard/cotizaciones"
        self.url_login = f"{self.base_url}/portal/login"
        self.url_balances = f"{self.base_url}/portal/saldos"
        self.timeout = HTTP_TIMEOUT
        self.exclude_symbols = set(EXCLUDE_SYMBOLS)
        
        self.email = os.getenv("MERCOSUR_EMAIL") or os.getenv("MERCOSUR_USER", "")
        self.password = os.getenv("MERCOSUR_PASSWORD", "")
        self.token = None
        self.user_data = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json"
        }

    def login(self, force=False):
        if self.token and self.token != "GUEST_TOKEN" and not force:
            return True

        load_dotenv()
        self.email = os.getenv("MERCOSUR_EMAIL") or os.getenv("MERCOSUR_USER", self.email)
        self.password = os.getenv("MERCOSUR_PASSWORD", self.password)

        if not self.email or not self.password:
            self.token = "GUEST_TOKEN"
            self.user_data = {"username": "Guest", "role": "public"}
            return True

        try:
            payload = {
                "email": self.email,
                "username": self.email,
                "password": self.password
            }
            res = requests.post(self.url_login, json=payload, headers=self.headers, timeout=self.timeout)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("success") and data.get("token"):
                    self.token = data.get("token")
                    self.user_data = data.get("cliente", {})
                    self.headers["Authorization"] = f"Bearer {self.token}"
                    return True
            
            self.token = "GUEST_TOKEN"
            return False

        except Exception:
            self.token = "GUEST_TOKEN"
            return False

    def authenticate(self):
        return self.login()

    def _request_with_auth_retry(self, method, url, **kwargs):
        if not self.token or self.token == "GUEST_TOKEN":
            self.login()

        kwargs["headers"] = self.headers
        res = requests.request(method, url, **kwargs)

        if res.status_code in (401, 403):
            if self.login(force=True):
                kwargs["headers"] = self.headers
                res = requests.request(method, url, **kwargs)

        return res

    @staticmethod
    def _to_float(value, default=0.0):
        """Convierte valores de la API a float tolerando None, 'N/A' y formato '1.234,56'."""
        if isinstance(value, bool) or value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(" ", "").replace("\u00a0", "")
        if not text:
            return default
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif text.count(",") == 1 and len(text.split(",")[-1]) <= 2:
            text = text.replace(",", ".")
        try:
            return float(text)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _pick(record, *keys):
        """Primer valor no nulo entre varias claves posibles del registro."""
        for key in keys:
            if isinstance(record, dict) and record.get(key) is not None:
                return record[key]
        return None

    def get_balances(self):
        try:
            res = self._request_with_auth_retry("GET", self.url_balances, timeout=self.timeout)
            
            if res.status_code in (200, 304):
                response_json = res.json()
                accounts = response_json.get("data", response_json) if isinstance(response_json, dict) else response_json
                if isinstance(accounts, dict):
                    accounts = [accounts]

                disponible = 0.0
                actual = 0.0
                bloqueado = 0.0

                for acc in accounts:
                    if isinstance(acc, dict):
                        disponible += self._to_float(self._pick(acc, "disponible", "saldo_disponible", "available_balance"))
                        actual += self._to_float(self._pick(acc, "total", "saldo_actual", "saldo", "current_balance", "total_balance"))
                        bloqueado += self._to_float(self._pick(acc, "bloqueado", "bloqueos", "blocked_balance", "blocked_funds"))

                return {
                    "disponible": disponible,
                    "saldo_disponible": disponible,
                    "ves_available": disponible,
                    "available_balance": disponible,
                    "actual": actual,
                    "saldo_actual": actual,
                    "total": actual,
                    "total_balance": actual,
                    "bloqueado": bloqueado,
                    "blocked_balance": bloqueado,
                    "raw_data": accounts
                }

            return dict(self._empty_balances())
        except Exception:
            return dict(self._empty_balances())

    @staticmethod
    def _empty_balances():
        """Estructura de saldos en cero con todos los alias que usa la UI/IA."""
        return {
            "disponible": 0.0, "saldo_disponible": 0.0, "ves_available": 0.0,
            "available_balance": 0.0, "actual": 0.0, "saldo_actual": 0.0,
            "total": 0.0, "total_balance": 0.0, "bloqueado": 0.0,
            "blocked_balance": 0.0, "raw_data": [],
        }

    def get_available_balance(self):
        """Atajo: saldo disponible en VES (0.0 si no se puede consultar)."""
        return self._to_float(self.get_balances().get("disponible"))

    def fetch_quotes(self):
        try:
            response = requests.get(self.url_quotes, headers=self.headers, timeout=self.timeout)
            if response.status_code not in (200, 304):
                return []

            data = response.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                return []

            def parse_item(item):
                if not isinstance(item, dict):
                    return None
                symbol = str(self._pick(item, "cod_simb", "simbolo", "symbol") or "").strip().upper()
                if not symbol or symbol in self.exclude_symbols:
                    return None
                name = self._pick(item, "descripcion", "desc_simb", "description") or "Sin Nombre"
                price = self._to_float(self._pick(item, "precio_ultimo", "last_price"))
                var_pct = self._to_float(self._pick(item, "variacion_rel", "var_pct", "variacion"))
                traded_cash = self._to_float(
                    self._pick(item, "monto_efectivo_acumulado", "monto_efectivo", "cash_amount")
                )
                dividend_type = item.get("tipo_dividendo") or "N/A"

                return {
                    "symbol": symbol,
                    "description": name,
                    # Nombres de la API + alias usados por la IA y la interfaz
                    "last_price": price,
                    "precio_ultimo": price,
                    "var_pct": var_pct,
                    "relative_variation_pct": var_pct,
                    "cash_amount": traded_cash,
                    "monto_efectivo": traded_cash,
                    "dividends": dividend_type,
                    "tipo_dividendo": dividend_type,
                }

            # Procesamiento concurrente de los instrumentos para máxima velocidad
            with ThreadPoolExecutor(max_workers=8) as executor:
                parsed = executor.map(parse_item, items)
            quotes = [quote for quote in parsed if quote]

            self._save_quotes_backup(quotes)
            return quotes

        except Exception:
            return []

    @staticmethod
    def _save_quotes_backup(quotes):
        """Guarda copia local de las cotizaciones (data/cotizaciones.json + quotes_latest.json)."""
        for path in (QUOTES_FILE, QUOTES_LATEST_FILE):
            if not path:
                continue
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(quotes, handle, ensure_ascii=False, indent=2)
            except Exception:
                continue

    def get_companies_summary(self):
        return self.fetch_quotes()

    def fetch_orders(self, pagina=1, limite=20):
        try:
            url_orders = f"{self.base_url}/portal/ordenes?pagina={pagina}&limite={limite}"
            response = self._request_with_auth_retry("GET", url_orders, timeout=self.timeout)
            
            if response.status_code not in (200, 304):
                return []

            data = response.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                items = [items]

            orders = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                orders.append({
                    "id": item.get("id"),
                    "tipo": item.get("tipo"),
                    "symbol": item.get("cod_simb"),
                    "status": item.get("estado"),
                    "date": item.get("fecha_orden"),
                    "requested_qty": float(item.get("cantidad_solicitada") or 0.0),
                    "requested_price": float(item.get("precio_solicitado") or 0.0),
                    "executed_qty": float(item.get("cantidad_ejecutada") or 0.0),
                    "blocked_amount": float(item.get("monto_bloqueo_solicitud") or 0.0),
                    "title_desc": item.get("desc_titulo")
                })

            return orders
        except Exception:
            return []
