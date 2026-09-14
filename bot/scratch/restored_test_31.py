import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

balances = client.get_balances()
account_id = balances.get("account_id", 4391)

# Step 1: validar-precio
res1 = client.session.post(
    "https://cm.mercosur.com.ve/portal/ordenes/validar-precio",
    json={"cod_simb": "BNC", "precio": 235.0, "tipo_precio": "LIMIT"}
)
print("1. validar-precio:", res1.status_code, res1.text)

# Step 2: calcular-costos
res2 = client.session.post(
    "https://cm.mercosur.com.ve/portal/ordenes/calcular-costos",
    json={"cod_simb": "BNC", "cantidad": 1, "precio": 235.0, "tipo_precio": "LIMIT", "tipo_operacion": "COMPRA"}
)
print("2. calcular-costos:", res2.status_code, res2.text)

# Step 3: create order with tipo_operacion instead of tipo, or both!
order_payload = {
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "tipo_operacion": "COMPRA",
    "tipo": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "declaracion_jurada": True,
    "clave_operaciones": "131100"
}

res3 = client.session.post(
    "https://cm.mercosur.com.ve/portal/ordenes",
    json=order_payload
)
print("3. POST /portal/ordenes:", res3.status_code, res3.text)
