import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal"
balances = client.get_balances()
account_id = balances.get("account_id", 4391)

base_item = {
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "tipo": "COMPRA",
    "tipo_operacion": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT"
}

variations = [
    {"declaracion_jurada": True},
    {"acepta_declaracion_jurada": True},
    {"acepta_declaracion": True},
    {"declaracion": True},
    {"declaracion_origen_fondos": True},
    {"declaracion_jurada": "SI"},
    {"declaracion_jurada": "true"},
    {"declaracion_jurada": 1},
    {"declaracion_jurada": {"version": "v1"}},
    {"declaracion": {"version": "v1", "aceptada": True}},
    {"acepta_terminos": True},
    {"declaracion_aceptada": True},
    {"declaracion_jurada": True, "acepta_declaracion_jurada": True, "declaracion_origen_fondos": True},
]

for var in variations:
    payload = {**base_item, **var}
    res = client.session.post(f"{base}/carrito/items", json=payload)
    if "declaración jurada" not in res.text.lower():
        print(f"🎉 SUCCESS! {var} -> Status {res.status_code}: {res.text}")
    else:
        print(f"NO: {var} -> {res.text}")
