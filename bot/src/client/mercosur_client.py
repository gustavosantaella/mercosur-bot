import json
import requests
from pathlib import Path
from src.config import TOKEN_FILE, MERCOSUR_EMAIL, MERCOSUR_PASSWORD, MERCOSUR_CLAVE_OPERACIONES

class MercosurClient:
    def __init__(self):
        self.base_url = "https://clientsapp.mercosur.com.ve"
        self.email = MERCOSUR_EMAIL
        self.password = MERCOSUR_PASSWORD
        self.clave_operaciones = MERCOSUR_CLAVE_OPERACIONES
        self.token = ""
        self.client_info = {}

        self.session = requests.Session()
        self.load_token_from_file()

    @property
    def user_data(self):
        return self.client_info

    @user_data.setter
    def user_data(self, value):
        self.client_info = value

    def load_token_from_file(self):
        token_path = Path(TOKEN_FILE)
        if token_path.exists():
            try:
                with open(token_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tok = data.get("token")
                    self.token = str(tok) if tok is not None else ""
                    self.client_info = data.get("client_info") or data.get("user_data", {})
            except Exception:
                self.token = ""

    def save_token_to_file(self):
        token_path = Path(TOKEN_FILE)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as f:
            json.dump({
                "token": self.token,
                "client_info": self.client_info,
                "user_data": self.client_info
            }, f, indent=4)

    def get_headers(self):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://clientsapp.mercosur.com.ve",
            "Referer": "https://clientsapp.mercosur.com.ve/",
            "Sec-Ch-Ua": '"Chromium";v="152", "Not?A_Brand";v="24", "Google Chrome";v="152"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _find_token_in_dict(self, data):
        if isinstance(data, dict):
            for k in ["token", "accessToken", "access_token", "jwt", "bearer"]:
                if k in data and isinstance(data[k], str) and data[k]:
                    return data[k]
            for v in data.values():
                found = self._find_token_in_dict(v)
                if found:
                    return found
        return None

    def login(self):
        # Si ya existe un token valido en cache, lo reutiliza directamente sin re-autenticar por HTTP
        if self.token:
            return self.token

        url = f"{self.base_url}/login"
        payload = {
            "email": self.email,
            "password": self.password
        }
        response = self.session.post(url, json=payload, headers=self.get_headers())

        if response.status_code != 200:
            raise Exception(f"Login fallido: HTTP {response.status_code} - {response.text}")

        data = response.json()
        extracted_token = self._find_token_in_dict(data)

        if not extracted_token:
            raise Exception("No se pudo localizar un JWT/token valido en el payload de respuesta de login.")

        self.token = str(extracted_token)
        self.client_info = data.get("user") or data.get("client") or (data if isinstance(data, dict) else {})

        self.save_token_to_file()
        return self.token

    def get_balances(self):
        url = "https://cm.mercosur.com.ve/portal/saldos"
        response = self.session.get(url, headers=self.get_headers())

        if response.status_code != 200:
            raise Exception(f"Failed to fetch Mercosur account balance: HTTP {response.status_code} - {response.text}")

        return response.json()

    def get_quotes(self):
        url = "https://cm.mercosur.com.ve/portal/mercado/dashboard/cotizaciones"
        response = self.session.get(url, headers=self.get_headers())

        if response.status_code != 200:
            raise Exception(f"Failed to fetch quotes: HTTP {response.status_code} - {response.text}")

        return response.json()
