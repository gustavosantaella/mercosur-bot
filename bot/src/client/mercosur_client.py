import os
import json
import socket
import urllib3
import requests
from dotenv import load_dotenv

# Deshabilitar warnings de HTTPS no verificado
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

DNS_SERVERS = [
    "8.8.8.8",
    "1.1.1.1",
    "200.44.32.12",
    "200.44.32.13",
    "9.9.9.9"
]

def get_custom_dns_ip(host):
    """Resuelve la IP usando DNS alternativos."""
    try:
        import dns.resolver
        for dns_ip in DNS_SERVERS:
            try:
                resolver = dns.resolver.Resolver(configure=False)
                resolver.nameservers = [dns_ip]
                resolver.timeout = 2
                resolver.lifetime = 2
                answers = resolver.resolve(host, 'A')
                for rdata in answers:
                    return str(rdata)
            except Exception:
                continue
    except ImportError:
        pass
    
    return socket.gethostbyname(host)

# Monkey-patch para forzar la resolución DNS manteniendo SSL intacto
_original_getaddrinfo = socket.getaddrinfo

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == "cm.mercosur.com.ve":
        ip = get_custom_dns_ip(host)
        return _original_getaddrinfo(ip, port, family, type, proto, flags)
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = patched_getaddrinfo

class MercosurClient:
    def __init__(self):
        self.url_quotes = "https://cm.mercosur.com.ve/portal/mercado/dashboard/cotizaciones"
        self.url_login = "https://cm.mercosur.com.ve/portal/auth/login"
        self.url_balances = "https://cm.mercosur.com.ve/portal/saldos"
        self.username = os.getenv("MERCOSUR_USER", "")
        self.password = os.getenv("MERCOSUR_PASSWORD", "")
        self.token = None
        self.user_data = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }

    def login(self):
        if not self.username or not self.password:
            print("⚠️ [Mercosur] Sin credenciales configuradas en .env. Modo lectura/público activado.")
            self.token = "GUEST_TOKEN"
            self.user_data = {"username": "Guest", "role": "public"}
            return True

        try:
            payload = {"username": self.username, "password": self.password}
            res = requests.post(self.url_login, json=payload, headers=self.headers, timeout=12)
            
            if res.status_code == 200:
                data = res.json()
                self.token = data.get("token") or data.get("access_token") or "AUTH_SUCCESS"
                self.user_data = data.get("user") or data.get("data") or {"username": self.username}
                self.headers["Authorization"] = f"Bearer {self.token}"
                print("🔑 [Mercosur] Autenticación exitosa.")
                return True
            else:
                self.token = "GUEST_TOKEN"
                return False

        except Exception as e:
            print(f"⚠️ [Mercosur] Fallo al autenticar: {e}")
            self.token = "GUEST_TOKEN"
            return False

    def authenticate(self):
        return self.login()

    def get_balances(self):
        try:
            res = requests.get(self.url_balances, headers=self.headers, timeout=12)
            if res.status_code in (200, 304):
                response_json = res.json()
                accounts = response_json.get("data", [])
                
                ves_available = 0.0
                ves_actual = 0.0
                usd_available = 0.0

                for acc in accounts:
                    moneda = acc.get("moneda", "VES")
                    if moneda == "VES":
                        ves_available += float(acc.get("saldo_disponible", 0.0))
                        ves_actual += float(acc.get("saldo_actual", 0.0))
                    elif moneda in ("USD", "USDT"):
                        usd_available += float(acc.get("saldo_disponible", 0.0))

                return {
                    "ves_available": ves_available,
                    "ves_actual": ves_actual,
                    "usd_available": usd_available,
                    "raw_data": accounts
                }
                
            return {"ves_available": 0.0, "usd_available": 0.0}
        except Exception as e:
            print(f"⚠️ [Mercosur] Error al consultar saldos: {e}")
            return {"ves_available": 0.0, "usd_available": 0.0}

    def fetch_quotes(self):
        try:
            response = requests.get(self.url_quotes, headers=self.headers, timeout=12)
            if response.status_code != 200:
                return []

            data = response.json()
            quotes = []
            items = data.get("data", data) if isinstance(data, dict) else data

            for item in items:
                symbol = item.get("simbolo") or item.get("ticker") or item.get("symbol") or "N/A"
                name = item.get("descripcion") or item.get("nombre") or item.get("empresa") or "Sin Nombre"
                price = float(item.get("precio_ultimo") or item.get("ultimo") or item.get("precio") or 0.0)
                var_pct = float(item.get("variacion") or item.get("variacion_pct") or 0.0)
                cash_div = float(item.get("monto_efectivo") or 0.0)
                dividend_type = item.get("tipo_dividendo") or "N/A"

                quotes.append({
                    "symbol": symbol,
                    "description": name,
                    "last_price": price,
                    "var_pct": var_pct,
                    "cash_amount": cash_div,
                    "dividends": dividend_type
                })

            with open("quotes_latest.json", "w", encoding="utf-8") as f:
                json.dump(quotes, f, ensure_ascii=False, indent=2)

            return quotes

        except Exception:
            return []

    def get_companies_summary(self):
        return self.fetch_quotes()
