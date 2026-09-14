import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base_payload = {
    "cuenta_id": 4391,
    "cartera_id": 4391,
    "tipo": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "clave_operaciones": "131100"
}

headers_list = [
    {"X-Declaracion-Jurada": "true"},
    {"X-Acepta-Declaracion": "true"},
    {"X-Declaracion": "true"},
    {"Declaracion-Jurada": "true"},
]

for h in headers_list:
    r = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=base_payload, headers=h)
    print(f"Header {h} -> Status {r.status_code}: {r.text}")

# Test parameters in body with various types/values:
body_tests = [
    {"declaracion_jurada": True, "aceptar_declaracion_jurada": True},
    {"declaracion_jurada": True, "declaracion_jurada_origen_fondos": True},
    {"declaracion_jurada": "SI", "acepta": True},
    {"declaracion_jurada": 1, "declaracion": 1},
    {"acepta_declaracion_jurada": True, "declaracion_jurada": True},
    {"declaracion_jurada": "1", "acepta_declaracion_jurada": "1"},
    {"declaracion_jurada": True, "declaracion_origen_fondos": True, "acepta_declaracion_jurada": True},
    {"declaraciones": ["declaracion_jurada", "origen_fondos"]},
    {"declaracion_jurada_aceptada": 1},
    {"declaraciones_aceptadas": [True]},
    {"declaracion": True, "declaracion_jurada": True, "clave_operaciones": "131100"},
]

for b in body_tests:
    p = {**base_payload, **b}
    r = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=p)
    if "DECLARACION_REQUERIDA" not in r.text:
        print(f"[FOUND!] Body {b} -> Status {r.status_code}: {r.text}")
    else:
        print(f"[NO] {b} -> {r.text}")
