import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

balances = client.get_balances()
account_id = balances.get("account_id", 4391)

print("1. Calling validar-precio...")
r1 = client.session.post(
    "https://cm.mercosur.com.ve/portal/ordenes/validar-precio",
    json={"cod_simb": "BNC", "precio": 235.0, "tipo_precio": "LIMIT"}
)
print("  Status:", r1.status_code, r1.text)

print("2. Calling calcular-costos...")
r2 = client.session.post(
    "https://cm.mercosur.com.ve/portal/ordenes/calcular-costos",
    json={"cod_simb": "BNC", "cantidad": 1, "precio": 235.0, "tipo_precio": "LIMIT", "tipo_operacion": "COMPRA"}
)
print("  Status:", r2.status_code, r2.text)

# Step 3: Test POST /portal/ordenes with variations after calling pre-validation endpoints
base_payload = {
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "tipo": "COMPRA",
    "tipo_operacion": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "clave_operaciones": "131100"
}

decl_variations = [
    {"declaracion_jurada": True},
    {"declaracion_jurada": True, "acepta_declaracion_jurada": True},
    {"declaracion": True, "declaracion_jurada": True},
    {"declaracion": {"version": "v1", "aceptada": True}},
    {"declaracion_jurada": "SI"},
    {"declaracion_jurada": 1},
]

for d in decl_variations:
    p = {**base_payload, **d}
    res = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=p)
    if "DECLARACION_REQUERIDA" not in res.text:
        print(f"🎉 FOUND ORDER PAYLOAD! {d} -> Status {res.status_code}: {res.text}")
    else:
        print(f"NO: {d} -> {res.text}")
