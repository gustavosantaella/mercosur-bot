import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal"
balances = client.get_balances()
account_id = balances.get("account_id", 4391)

# Step 1: Pre-validations (optional/recommended)
print("1. Pre-validation...")
client.session.post(f"{base}/ordenes/validar-precio", json={"cod_simb": "BNC", "precio": 235.0, "tipo_precio": "LIMIT"})
client.session.post(f"{base}/ordenes/calcular-costos", json={"cod_simb": "BNC", "cantidad": 1, "precio": 235.0, "tipo_precio": "LIMIT", "tipo_operacion": "COMPRA"})

# Step 2: Add item to cart (POST /portal/carrito/items)
item_payload = {
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "tipo": "COMPRA",
    "tipo_operacion": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT"
}

print("2. Adding item to cart (POST /portal/carrito/items)...")
r_add = client.session.post(f"{base}/carrito/items", json=item_payload)
print("  Status:", r_add.status_code, r_add.text)

# Step 3: Check cart contents
print("3. Checking cart contents (GET /portal/carrito)...")
r_cart = client.session.get(f"{base}/carrito")
print("  Cart content:", r_cart.text)

# Step 4: Execute cart (POST /portal/carrito/ejecutar)
print("4. Executing cart (POST /portal/carrito/ejecutar)...")
execute_payload = {
    "clave_operaciones": "131100",
    "declaracion_jurada": True,
    "declaracion": True,
    "acepta_declaracion": True
}
r_exec = client.session.post(f"{base}/carrito/ejecutar", json=execute_payload)
print("  Status:", r_exec.status_code, r_exec.text)
