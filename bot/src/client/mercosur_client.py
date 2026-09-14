import os
import json
import socket
import urllib3
import requests
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

    def login(self):
        load_dotenv()
        self.email = os.getenv("MERCOSUR_EMAIL") or os.getenv("MERCOSUR_USER", self.email)
        self.password = os.getenv("MERCOSUR_PASSWORD", self.password)

        print(f"🔍 [Debug] Intentando login con usuario: '{self.email}'")

        if not self.email or not self.password:
            print("⚠️ [Mercosur] Sin credenciales configuradas en .env. Modo lectura/público activado.")
            self.token = "GUEST_TOKEN"
            self.user_data = {"username": "Guest", "role": "public"}
            return True

        try:
            # Enviamos tanto email como username para cubrir ambas variantes del backend
            payload = {
                "email": self.email,
                "username": self.email,
                "password": self.password
            }
            res = requests.post(self.url_login, json=payload, headers=self.headers, timeout=12)
            
            if res.status_code == 200:
                data = res.json()
                if data.get("success") and data.get("token"):
                    self.token = data.get("token")
                    self.user_data = data.get("cliente", {})
                    self.headers["Authorization"] = f"Bearer {self.token}"
                    
                    token_preview = f"{self.token[:12]}...{self.token[-10:]}" if len(self.token) > 22 else self.token
                    nombre_cliente = self.user_data.get("nombre", "").strip()
                    
                    print(f"🔑 [Debug] Token recibido: {token_preview}")
                    print(f"🔑 [Mercosur] Autenticación exitosa. Bienvenido {nombre_cliente}.")
                    return True
            
            print(f"⚠️ [Mercosur] Fallo al autenticar (Status {res.status_code}). Respuesta backend: {res.text}")
            self.token = "GUEST_TOKEN"
            return False

        except Exception as e:
            print(f"⚠️ [Mercosur] Error de conexión en login: {e}")
            self.token = "GUEST_TOKEN"
            return False

    def authenticate(self):
        return self.login()

    def get_balances(self):
        if self.token == "GUEST_TOKEN" or not self.token:
            print("⚠️ [Mercosur] Sin sesión activa. Configura MERCOSUR_EMAIL y MERCOSUR_PASSWORD en .env.")
            return {"disponible": 0.0, "total": 0.0, "bloqueado": 0.0, "ves_available": 0.0}

        try:
            res = requests.get(self.url_balances, headers=self.headers, timeout=12)
            if res.status_code in (200, 304):
                response_json = res.json()
                
                # Manejar respuesta si devuelve array directo, diccionario o subclave "data"
                accounts = response_json.get("data", response_json) if isinstance(response_json, dict) else response_json
                if isinstance(accounts, dict):
                    accounts = [accounts]

                disponible = 0.0
                actual = 0.0
                bloqueado = 0.0

                for acc in accounts:
                    if isinstance(acc, dict):
                        disponible += float(acc.get("saldo_disponible") or acc.get("disponible") or 0.0)
                        actual += float(acc.get("saldo_actual") or acc.get("total") or acc.get("saldo") or 0.0)
                        bloqueado += float(acc.get("bloqueos") or acc.get("bloqueado") or 0.0)

                return {
                    "disponible": disponible,
                    "saldo_disponible": disponible,
                    "ves_available": disponible,
                    "actual": actual,
                    "saldo_actual": actual,
                    "ves_actual": actual,
                    "total": actual,
                    "bloqueado": bloqueado,
                    "bloqueos": bloqueado,
                    "raw_data": accounts
                }

            print(f"⚠️ [Mercosur] Status {res.status_code} al consultar saldos.")
            return {"disponible": 0.0, "total": 0.0, "bloqueado": 0.0}
        except Exception as e:
            print(f"⚠️ [Mercosur] Error al consultar saldos: {e}")
            return {"disponible": 0.0, "total": 0.0, "bloqueado": 0.0}

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
