import json
import requests
from typing import Dict, Any, List, Optional
from src.config import (
    MERCOSUR_LOGIN_URL,
    MERCOSUR_COTIZACIONES_URL,
    MERCOSUR_SALDOS_URL,
    MERCOSUR_ORDENES_URL,
    MERCOSUR_EMAIL,
    MERCOSUR_PASSWORD,
    MERCOSUR_CLAVE_OPERACIONES,
    TOKEN_FILE,
    EXCLUDE_SYMBOLS
)
from pathlib import Path

from src.ai.dividends import get_dividend_info

class MercosurClient:
    """
    Client for Mercosur Casa de Bolsa API.
    Handles JWT authentication with local persistence in data/session_token.json
    and auto-renewal if token expires or API returns authentication errors (401/403).
    """

    def __init__(self, email: str = MERCOSUR_EMAIL, password: str = MERCOSUR_PASSWORD):
        self.email = email
        self.password = password
        self.token: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
            "Origin": "https://clientsapp.mercosur.com.ve",
            "Referer": "https://clientsapp.mercosur.com.ve/",
            "Accept": "*/*"
        })

        # Load previously saved token if available
        self.load_token_from_file()

    def load_token_from_file(self) -> bool:
        """
        Loads persisted JWT token from TOKEN_FILE (data/session_token.json).
        """
        try:
            Path(TOKEN_FILE).mkdir(parents=True, exist_ok=True)
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                token = data.get("token")
                if token:
                        self.token = token
                        self.user_data = data.get("cliente")
                        self.session.headers.update({
                            "Authorization": f"Bearer {self.token}"
                        })
        except Exception as e:
            print(f"[Warning] Failed to load saved token: {e}")
        return False

    def save_token_to_file(self, token: str, user_data: Optional[Dict[str, Any]] = None):
        """
        Saves JWT token and client user data to TOKEN_FILE (data/session_token.json).
        """
        try:
            payload = {
                "token": token,
                "cliente": user_data
            }
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Warning] Failed to save token to disk: {e}")

    def login(self, force: bool = False) -> str:
        """
        Logs in or reuses saved token.
        If force=False and cached token exists, it reuses it.
        If force=True or no token exists, performs POST request to /portal/login.
        """
        if not force and self.token:
            return self.token

        payload = {
            "email": self.email,
            "password": self.password
        }
        response = self.session.post(MERCOSUR_LOGIN_URL, json=payload, timeout=15)
        
        if response.status_code != 200:
            raise Exception(f"Login request failed: HTTP {response.status_code} - {response.text}")
        
        data = response.json()
        if not data.get("success"):
            raise Exception(f"Login unsuccessful: {data.get('error', 'Unknown error')}")
        
        self.token = data.get("token")
        self.user_data = data.get("cliente")
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })

        self.save_token_to_file(self.token, self.user_data)
        return self.token

    def get_quotes(self) -> List[Dict[str, Any]]:
        """
        Fetches current quotes from /portal/mercado/dashboard/cotizaciones.
        Automatically re-authenticates if API rejects token (401/403).
        """
        if not self.token:
            self.login(force=True)

        response = self.session.get(MERCOSUR_COTIZACIONES_URL, timeout=15)
        
        is_auth_error = response.status_code in (401, 403)
        if response.status_code == 200:
            try:
                res_json = response.json()
                if not res_json.get("success") and "auth" in str(res_json.get("error", "")).lower():
                    is_auth_error = True
            except Exception:
                pass

        if is_auth_error:
            print("[MercosurClient] Token expired or rejected. Re-authenticating via POST /portal/login...")
            self.login(force=True)
            response = self.session.get(MERCOSUR_COTIZACIONES_URL, timeout=15)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch quotes: HTTP {response.status_code} - {response.text}")
        
        result = response.json()
        if not result.get("success"):
            raise Exception(f"Unable to retrieve quotes: {result.get('error', 'Unknown error')}")
            
        return result.get("data", [])

    def get_balances(self) -> Dict[str, Any]:
        """
        Fetches client account balances from Mercosur Casa de Bolsa (/portal/saldos).
        """
        if not self.token:
            self.login(force=True)

        response = self.session.get(MERCOSUR_SALDOS_URL, timeout=15)

        is_auth_error = response.status_code in (401, 403)
        if is_auth_error:
            print("[MercosurClient] Token expired while fetching balances. Re-authenticating...")
            self.login(force=True)
            response = self.session.get(MERCOSUR_SALDOS_URL, timeout=15)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch Mercosur account balance: HTTP {response.status_code} - {response.text}")

        res_json = response.json()
        if not res_json.get("success"):
            raise Exception(f"Unable to retrieve account balance: {res_json.get('error', 'Unknown error')}")

        data_list = res_json.get("data", [])
        if not data_list:
            return {
                "available_balance": 0.0,
                "current_balance": 0.0,
                "blocked_funds": 0.0,
                "currency": "VES"
            }

        account = data_list[0]
        return {
            "account_id": account.get("id"),
            "account_name": account.get("nombre_cuenta", "Main Account"),
            "currency": account.get("moneda", "VES"),
            "available_balance": float(account.get("saldo_disponible") or 0.0),
            "current_balance": float(account.get("saldo_actual") or 0.0),
            "global_balance": float(account.get("saldo_global") or 0.0),
            "income": float(account.get("ingresos") or 0.0),
            "expenses": float(account.get("egresos") or 0.0),
            "blocked_funds": float(account.get("bloqueos") or 0.0)
        }

    def create_order(
        self,
        order_type: str,
        symbol: str,
        quantity: float,
        price: float,
        price_type: str = "LIMIT",
        clave_operaciones: Optional[str] = None,
        account_id: Optional[int] = None,
        portfolio_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submits a BUY or SELL order to Mercosur Casa de Bolsa via POST /portal/ordenes.
        """
        if not self.token:
            self.login(force=True)

        pin = clave_operaciones or MERCOSUR_CLAVE_OPERACIONES

        if not account_id:
            balances = self.get_balances()
            account_id = balances.get("account_id", 4391)

        if not portfolio_id:
            portfolio_id = account_id

        # 1. Price validation check
        try:
            val_url = MERCOSUR_ORDENES_URL.rstrip('/') + '/validar-precio'
            self.session.post(val_url, json={
                "cod_simb": symbol.upper(),
                "precio": float(price),
                "tipo_precio": price_type
            }, timeout=10)
        except Exception:
            pass

        # 2. Cost calculation check
        try:
            calc_url = MERCOSUR_ORDENES_URL.rstrip('/') + '/calcular-costos'
            self.session.post(calc_url, json={
                "cod_simb": symbol.upper(),
                "cantidad": float(quantity),
                "precio": float(price),
                "tipo_precio": price_type,
                "tipo_operacion": order_type.upper()
            }, timeout=10)
        except Exception:
            pass

        payload = {
            "tipo": order_type.upper(),
            "tipo_operacion": order_type.upper(),
            "cod_simb": symbol.upper(),
            "cantidad": quantity,
            "precio": price,
            "tipo_precio": price_type,
            "cuenta_id": account_id,
            "cartera_id": portfolio_id,
            "declaracion_jurada": True,
            "acepta_declaracion_jurada": True,
            "clave_operaciones": pin
        }

        response = self.session.post(MERCOSUR_ORDENES_URL, json=payload, timeout=15)

        if response.status_code in (401, 403):
            print("[MercosurClient] Token expired while submitting order. Re-authenticating...")
            self.login(force=True)
            response = self.session.post(MERCOSUR_ORDENES_URL, json=payload, timeout=15)

        if response.status_code not in (200, 201):
            res_text = response.text
            if "DECLARACION_REQUERIDA" in res_text:
                print(f"[MercosurClient] DECLARACION_REQUERIDA received from REST API. Launching automated Selenium browser flow to accept declaration & submit order...")
                from src.client.selenium_trader import execute_selenium_order
                res = execute_selenium_order(
                    symbol=symbol,
                    quantity=int(quantity),
                    price=float(price),
                    order_type=order_type,
                    pin=pin
                )
                if res.get("success"):
                    return res
                raise Exception(f"Order submission failed via Selenium: {res.get('error')}")

            raise Exception(f"Failed to submit order ({order_type} {symbol}): HTTP {response.status_code} - {res_text}")

        res_json = response.json()
        if not res_json.get("success"):
            raise Exception(f"Order rejected ({order_type} {symbol}): {res_json.get('error', 'Unknown error')}")

        return res_json.get("data", {})



    def get_companies_summary(self) -> List[Dict[str, Any]]:
        """
        Processes and cleans stock quotes for listed companies,
        filtering out symbols defined in EXCLUDE_SYMBOLS (.env).
        """
        raw_data = self.get_quotes()
        companies = []
        
        for item in raw_data:
            symbol = (item.get("cod_simb") or "").strip().upper()
            if not symbol or symbol in EXCLUDE_SYMBOLS:
                continue

            div_info = get_dividend_info(symbol)
            
            companies.append({
                "symbol": symbol,
                "name": item.get("descripcion") or symbol,
                "last_price": float(item.get("precio_ultimo") or 0.0),
                "relative_variation_pct": float(item.get("variacion_rel") or 0.0),
                "cash_amount": float(item.get("monto_efectivo_acumulado") or 0.0),
                "volume": float(item.get("volumen_acumulado") or 0.0),
                "buy_price": float(item.get("precio_compra") or 0.0) if item.get("precio_compra") else None,
                "sell_price": float(item.get("precio_venta") or 0.0) if item.get("precio_venta") else None,
                "market_type": item.get("tipo_mercado"),
                "sparkline": item.get("sparkline", []),
                "dividends": div_info
            })
            
        return companies


