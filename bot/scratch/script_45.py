import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal"

fields = [
    {"declaracion_jurada": True},
    {"acepta_declaracion_jurada": True},
    {"declaracion_origen_fondos": True},
    {"acepta_declaracion": True},
    {"declaracion": True},
    {"estado_kyc": "COMPLETO", "declaracion_jurada": True},
    {"declaracion_jurada_version": "v1"},
    {"version_declaracion": "v1"},
]

for f in fields:
    r = client.session.put(f"{base}/me", json=f)
    print(f"PUT /me {f} -> Status {r.status_code}: {r.text}")

# Now test adding item to cart or submitting order
balances = client.get_balances()
account_id = balances.get("account_id", 4391)

order_payload = {
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "tipo": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "declaracion_jurada": True,
    "clave_operaciones": "131100"
}

r_order = client.session.post(f"{base}/ordenes", json=order_payload)
print("\nTest POST /portal/ordenes after PUT /me:")
print("Status:", r_order.status_code, r_order.text)
