import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base_url = "https://cm.mercosur.com.ve/portal"

post_endpoints = [
    "/declaracion-jurada",
    "/declaracion-jurada/aceptar",
    "/declaracion-jurada/acepto",
    "/declaracion-jurada/firmar",
    "/declaracion-jurada/version",
    "/declaracion-jurada/v1",
    "/declaraciones/aceptar",
]

for ep in post_endpoints:
    r = client.session.post(base_url + ep, json={"version": "v1", "aceptada": True, "acepto": True})
    print(f"POST {ep} -> Status {r.status_code}: {r.text}")

# Also test POST /portal/ordenes with declaracion_version or declaracion parameters
ordenes_payloads = [
    {"declaracion_version": "v1"},
    {"declaracion_jurada_version": "v1"},
    {"acepta_declaracion_jurada": "v1"},
    {"declaracion": "v1"},
    {"declaracion_jurada": "v1"},
    {"declaracion": {"version": "v1"}},
    {"declaracion_jurada": {"version": "v1"}},
]

base_order = {
    "cuenta_id": 4391,
    "cartera_id": 4391,
    "tipo": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "clave_operaciones": "131100"
}

for op in ordenes_payloads:
    payload = {**base_order, **op}
    r = client.session.post(base_url + "/ordenes", json=payload)
    if "DECLARACION_REQUERIDA" not in r.text:
        print(f"🎉 FOUND SUCCESS IN ORDENES! {op} -> Status {r.status_code}: {r.text}")
    else:
        print(f"NO: {op} -> {r.text}")
