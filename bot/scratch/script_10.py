import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

# Let's inspect get_balances to be sure account_id
balances = client.get_balances()
print("Balances:", balances)

account_id = balances.get("account_id", 4391)

# Base order parameters
base_order = {
    "tipo": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "clave_operaciones": "131100"
}

variations = [
    {"declaracion_jurada": True},
    {"declaracion_jurada": 1},
    {"declaracion_jurada": "SI"},
    {"declaracion_jurada": "true"},
    {"acepta_declaracion": True},
    {"acepta_declaracion_jurada": True},
    {"declaracion": True},
    {"declaracion_origen_fondos": True},
    {"declaracionJurada": True},
    {"aceptaDeclaracionJurada": True},
    {"aceptaDeclaracion": True},
    {"declaracion_aceptada": True},
    {"declaracionAceptada": True},
    {"aceptar_declaracion": True},
    {"confirmacion_declaracion": True},
    {"declaracion_jurada": True, "declaracion_origen_fondos": True},
]

for i, var in enumerate(variations):
    payload = {**base_order, **var}
    r = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=payload, timeout=10)
    print(f"Variation {i} {var}: Status {r.status_code} -> {r.text}")
