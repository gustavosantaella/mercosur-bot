import os
import json
import socket
import urllib3
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

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
        self.base_url = "https://cm.mercosur.com.ve"
        self.url_quotes = f"{self.base_url}/portal/mercado/dashboard/cotizaciones"
        self.url_login = f"{self.base_url}/portal/login"
        self.url_balances = f"{self.base_url}/portal/saldos"
        
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
            res = requests.post(self.url_login, json=payload, headers=self.headers, timeout=8)
            
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

    def get_balances(self):
        try:
            res = self._request_with_auth_retry("GET", self.url_balances, timeout=8)
            
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
                        disponible += float(acc.get("disponible") or acc.get("saldo_disponible") or 0.0)
                        actual += float(acc.get("total") or acc.get("saldo_actual") or acc.get("saldo") or 0.0)
                        bloqueado += float(acc.get("bloqueado") or acc.get("bloqueos") or 0.0)

                return {
                    "disponible": disponible,
                    "saldo_disponible": disponible,
                    "ves_available": disponible,
                    "actual": actual,
                    "total": actual,
                    "bloqueado": bloqueado,
                    "raw_data": accounts
                }

            return {"disponible": 0.0, "total": 0.0, "bloqueado": 0.0, "ves_available": 0.0}
        except Exception:
            return {"disponible": 0.0, "total": 0.0, "bloqueado": 0.0, "ves_available": 0.0}

    def fetch_quotes(self):
        try:
            response = requests.get(self.url_quotes, headers=self.headers, timeout=8)
            if response.status_code not in (200, 304):
                return []

            data = response.json()
            items = data.get("data", data) if isinstance(data, dict) else data

            def parse_item(item):
                symbol = item.get("cod_simb") or item.get("simbolo") or item.get("symbol") or "N/A"
                name = item.get("descripcion") or item.get("desc_simb") or "Sin Nombre"
                price = float(item.get("precio_ultimo") or 0.0)
                var_pct = float(item.get("variacion_rel") or item.get("variacion") or 0.0)
                cash_div = float(item.get("monto_efectivo_acumulado") or item.get("monto_efectivo") or 0.0)
                dividend_type = item.get("tipo_dividendo") or "N/A"

                return {
                    "symbol": symbol,
                    "description": name,
                    "last_price": price,
                    "var_pct": var_pct,
                    "cash_amount": cash_div,
                    "dividends": dividend_type
                }

            # Procesamiento concurrente de los 41+ instrumentos para máxima velocidad
            with ThreadPoolExecutor(max_workers=8) as executor:
                quotes = list(executor.map(parse_item, items))

            try:
                with open("quotes_latest.json", "w", encoding="utf-8") as f:
                    json.dump(quotes, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            return quotes

        except Exception:
            return []

    def get_companies_summary(self):
        return self.fetch_quotes()

    def fetch_orders(self, pagina=1, limite=20):
        try:
            url_orders = f"{self.base_url}/portal/ordenes?pagina={pagina}&limite={limite}"
            response = self._request_with_auth_retry("GET", url_orders, timeout=8)
            
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
