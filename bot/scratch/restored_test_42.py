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

more_keys = [
    "acepto_declaracion_jurada",
    "acepto_declaracion",
    "declaracion_origen",
    "declaracion_fondos",
    "origen_fondos",
    "acepta_origen_fondos",
    "aceptar_declaracion",
    "declaracion_jurada_origen_fondos",
    "declaraciones_aceptadas",
    "acepto",
    "acepta",
    "aceptado",
    "declaracion_origen_recursos",
    "origen_recursos",
    "acepta_origen_recursos",
    "declaracion_fondos_origen",
    "declaracion_jurada_aceptada",
    "declaracion_jurada_fondos"
]

for k in more_keys:
    res1 = client.session.post(f"{base}/carrito/items", json={**base_item, k: True})
    res2 = client.session.post(f"{base}/carrito/items", json={**base_item, k: "1"})
    res3 = client.session.post(f"{base}/carrito/items", json={**base_item, k: 1})
    
    for label, r in [("True", res1), ("'1'", res2), ("1", res3)]:
        if "declaración jurada" not in r.text.lower():
            print(f"🎉 FOUND SUCCESS! Key '{k}' ({label}) -> Status {r.status_code}: {r.text}")
