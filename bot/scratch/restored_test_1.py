import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal"

# 1. Check clave-operaciones/status
r_pin = client.session.get(f"{base}/clave-operaciones/status")
print("GET /clave-operaciones/status:", r_pin.status_code, r_pin.text)

# 2. Check GET /carrito
r_cart = client.session.get(f"{base}/carrito")
print("GET /carrito:", r_cart.status_code, r_cart.text)

balances = client.get_balances()
account_id = balances.get("account_id", 4391)

order_item = {
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "tipo": "COMPRA",
    "tipo_operacion": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT"
}

# 3. Test POST /carrito
r_add = client.session.post(f"{base}/carrito", json=order_item)
print("POST /carrito:", r_add.status_code, r_add.text)

# 4. Test POST /carrito/procesar or checkout endpoints
cart_endpoints = [
    (f"{base}/carrito/procesar", {"clave_operaciones": "131100", "declaracion_jurada": True}),
    (f"{base}/carrito/checkout", {"clave_operaciones": "131100", "declaracion_jurada": True}),
    (f"{base}/carrito/confirmar", {"clave_operaciones": "131100", "declaracion_jurada": True}),
    (f"{base}/carrito/ordenes", {"clave_operaciones": "131100", "declaracion_jurada": True}),
]

for ep, p in cart_endpoints:
    r = client.session.post(ep, json=p)
    print(f"POST {ep} -> Status {r.status_code}: {r.text[:200]}")
