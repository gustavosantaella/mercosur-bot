import base64
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

import requests
import urllib3
from dotenv import load_dotenv

try:
    from src.config import (
        EXCLUDE_SYMBOLS,
        HTTP_TIMEOUT,
        MERCOSUR_BASE_URL,
        MERCOSUR_PORTAFOLIO_URLS,
        QUOTES_FILE,
        QUOTES_LATEST_FILE,
        SESSION_TTL_HOURS,
        TOKEN_FILE,
        USE_QUOTES_CACHE,
    )
except Exception:  # pragma: no cover - permite importar el módulo de forma aislada
    EXCLUDE_SYMBOLS, HTTP_TIMEOUT = [], 8
    MERCOSUR_BASE_URL = "https://cm.mercosur.com.ve"
    MERCOSUR_PORTAFOLIO_URLS = [f"{MERCOSUR_BASE_URL}/portal/portafolio"]
    QUOTES_FILE = QUOTES_LATEST_FILE = TOKEN_FILE = None
    SESSION_TTL_HOURS, USE_QUOTES_CACHE = 12.0, True

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
        # Estado de la sesión y del origen de los datos (para la interfaz)
        self.session_reused = False
        self.last_quotes_source = "none"   # "live" | "cache" | "none"
        self.last_quotes_age_hours = 0.0
        self.portfolio_source = None
        
        self.email = os.getenv("MERCOSUR_EMAIL") or os.getenv("MERCOSUR_USER", "")
        self.password = os.getenv("MERCOSUR_PASSWORD", "")
        self.token = None
        self.user_data = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json"
        }

    # ─────────────────────────────────────────────────────────────
    # Sesión persistente (evita un POST de login en cada ejecución)
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _token_expired(token, saved_at=None):
        """True si el JWT está expirado (campo 'exp') o si superó el TTL configurado."""
        if not token:
            return True
        payload = {}
        try:
            part = str(token).split(".")[1]
            padding = "=" * (-len(part) % 4)
            payload = json.loads(base64.urlsafe_b64decode(part + padding).decode("utf-8", "replace"))
        except Exception:
            payload = {}

        exp = payload.get("exp")
        if isinstance(exp, (int, float)) and exp > 0:
            return datetime.now().timestamp() >= (float(exp) - 60)

        if saved_at:
            try:
                saved = datetime.fromisoformat(str(saved_at))
                return datetime.now() - saved > timedelta(hours=float(SESSION_TTL_HOURS))
            except (ValueError, TypeError):
                return True
        # Sin exp ni fecha de guardado: no confiar en el token
        return True

    def _load_cached_session(self) -> bool:
        """Intenta reutilizar el token guardado en disco. Devuelve True si es válido."""
        if not TOKEN_FILE:
            return False
        try:
            if not TOKEN_FILE.exists():
                return False
            with open(TOKEN_FILE, encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return False

        token = payload.get("token")
        if not token or self._token_expired(token, payload.get("saved_at")):
            self.clear_session()
            return False

        self.token = token
        self.user_data = payload.get("cliente") or payload.get("user_data") or {}
        self.headers["Authorization"] = f"Bearer {token}"
        self.session_reused = True
        return True

    def _save_session(self) -> None:
        """Guarda el token (y los datos del cliente) para reutilizarlo después."""
        if not TOKEN_FILE or not self.token or self.token == "GUEST_TOKEN":
            return
        try:
            TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, "w", encoding="utf-8") as handle:
                json.dump({
                    "token": self.token,
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "cliente": self.user_data,
                }, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clear_session(self) -> None:
        """Borra la sesión guardada (token inválido o logout)."""
        self.token = None
        self.session_reused = False
        self.headers.pop("Authorization", None)
        if not TOKEN_FILE:
            return
        try:
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
        except Exception:
            pass

    def logout(self):
        """Cierra la sesión local (y notifica el logout si la API lo permite)."""
        try:
            if self.token and self.token != "GUEST_TOKEN":
                requests.get(f"{self.base_url}/portal/logout", headers=self.headers, timeout=self.timeout)
        except Exception:
            pass
        self.clear_session()

    def login(self, force=False):
        if self.token and self.token != "GUEST_TOKEN" and not force:
            return True

        # 1) Intentar reutilizar la sesión guardada (salvo que se fuerce un login nuevo)
        if not force and self._load_cached_session():
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
                    self.session_reused = False
                    self._save_session()
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

    def _fetch_quotes_live(self):
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

            return quotes

        except Exception:
            return []

    def fetch_quotes(self, allow_cache=True):
        """Cotizaciones en vivo; si la API falla, usa la última copia local (modo offline)."""
        live = self._fetch_quotes_live()
        if live:
            self.last_quotes_source = "live"
            self.last_quotes_age_hours = 0.0
            self._save_quotes_backup(live)
            return live

        if not (allow_cache and USE_QUOTES_CACHE):
            self.last_quotes_source = "none"
            return []

        cached, age_hours = self._load_quotes_backup()
        if cached:
            self.last_quotes_source = "cache"
            self.last_quotes_age_hours = age_hours
            return cached

        self.last_quotes_source = "none"
        return []

    @staticmethod
    def _load_quotes_backup():
        """Última copia local válida de cotizaciones -> (quotes, horas de antigüedad)."""
        for path in (QUOTES_FILE, QUOTES_LATEST_FILE):
            if not path:
                continue
            try:
                if not path.exists():
                    continue
                modified = datetime.fromtimestamp(path.stat().st_mtime)
                age_hours = (datetime.now() - modified).total_seconds() / 3600.0
                with open(path, encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, list) and data:
                    return data, round(age_hours, 2)
            except Exception:
                continue
        return [], 0.0

    @staticmethod
    def _save_quotes_backup(quotes):
        """Guarda la copia local de cotizaciones (data/cotizaciones.json)."""
        if not QUOTES_FILE:
            return
        try:
            QUOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(QUOTES_FILE, "w", encoding="utf-8") as handle:
                json.dump(quotes, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_companies_summary(self):
        return self.fetch_quotes()

    # ─────────────────────────────────────────────────────────────
    # Cartera / posiciones (B9)
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_positions(items):
        """Normaliza posiciones de cartera tolerando distintos formatos de la API."""
        if isinstance(items, dict):
            for key in ("posiciones", "portafolio", "titulos", "cartera", "data", "items"):
                if isinstance(items.get(key), list):
                    items = items[key]
                    break
            else:
                items = [items] if (items.get("cod_simb") or items.get("simbolo")) else []

        if not isinstance(items, list):
            return []

        positions = []
        for item in items:
            if not isinstance(item, dict):
                continue
            symbol = str(
                item.get("cod_simb") or item.get("simbolo") or item.get("symbol") or ""
            ).strip().upper()
            if not symbol:
                continue

            quantity = MercosurClient._to_float(
                MercosurClient._pick(item, "cantidad_disponible", "cantidad", "tenencia", "titulos")
            )
            if quantity <= 0:
                continue

            avg_price = MercosurClient._to_float(
                MercosurClient._pick(item, "precio_promedio", "costo_promedio", "precio_compra")
            )
            market_price = MercosurClient._to_float(
                MercosurClient._pick(item, "precio_ultimo", "precio_mercado", "precio_actual")
            )
            market_value = MercosurClient._to_float(MercosurClient._pick(item, "valor_mercado", "valor_actual"))
            cost = MercosurClient._to_float(MercosurClient._pick(item, "monto_invertido", "costo_total"))
            if not cost and avg_price:
                cost = quantity * avg_price
            if not market_value and market_price:
                market_value = quantity * market_price
            pnl = (market_value - cost) if (market_value and cost) else \
                MercosurClient._to_float(item.get("ganancia"))

            positions.append({
                "symbol": symbol,
                "description": item.get("descripcion") or item.get("desc_titulo") or symbol,
                "quantity": round(quantity, 4),
                "avg_price": round(avg_price, 4),
                "market_price": round(market_price, 4),
                "market_value": round(market_value, 2),
                "cost": round(cost, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round((pnl / cost * 100.0), 2) if cost else 0.0,
            })
        return positions

    @staticmethod
    def enrich_positions(positions, quotes):
        """Recalcula valor de mercado y P&L con las cotizaciones del momento."""
        prices = {}
        for quote in quotes or []:
            if not isinstance(quote, dict):
                continue
            symbol = str(quote.get("symbol") or quote.get("simbolo") or "").upper()
            price = MercosurClient._to_float(quote.get("last_price", quote.get("precio_ultimo")))
            if symbol and price > 0:
                prices[symbol] = price

        enriched = []
        for position in positions or []:
            item = dict(position)
            symbol = str(item.get("symbol", "")).upper()
            price = prices.get(symbol) or MercosurClient._to_float(item.get("market_price"))
            quantity = MercosurClient._to_float(item.get("quantity"))
            cost = MercosurClient._to_float(item.get("cost"))

            if price:
                item["market_price"] = round(price, 4)
            if price and quantity:
                item["market_value"] = round(price * quantity, 2)
            item["pnl"] = round(MercosurClient._to_float(item.get("market_value")) - cost, 2)
            item["pnl_pct"] = round((item["pnl"] / cost * 100.0), 2) if cost else 0.0
            enriched.append(item)
        return enriched

    def fetch_portfolio(self, quotes=None, urls=None):
        """Posiciones de la cartera. Prueba varios endpoints y degrada sin romper.

        Retorna [] si ningún endpoint responde con posiciones válidas.
        """
        for url in list(urls or MERCOSUR_PORTAFOLIO_URLS or []):
            try:
                response = self._request_with_auth_retry("GET", url, timeout=self.timeout)
            except Exception:
                continue
            if getattr(response, "status_code", 0) not in (200, 304):
                continue
            try:
                data = response.json()
            except Exception:
                continue
            payload = data.get("data", data) if isinstance(data, dict) else data
            positions = self._parse_positions(payload)
            if positions:
                self.portfolio_source = url
                return self.enrich_positions(positions, quotes)

        self.portfolio_source = None
        return []

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
