import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = {
    "cuenta_id": 4391,
    "cartera_id": 4391,
    "tipo": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "clave_operaciones": "131100"
}

decl_tests = [
    {"declaracion": {"aceptada": True, "version": "v1"}},
    {"declaracion": {"version": "v1", "aceptada": True}},
    {"declaracion": {"version": "v1"}},
    {"declaracion": {"aceptada": True}},
    {"declaracion": {"acepta": True, "version": "v1"}},
    {"declaracion": {"aceptado": True}},
    {"declaracion": {"acepto": True}},
    {"declaracion": True, "version": "v1"},
    {"declaracion_jurada": {"aceptada": True, "version": "v1"}},
    {"declaracion": {"version": "v1", "fecha_aceptacion": "2026-09-14T00:00:00.000Z"}},
    {"declaracion_jurada": {"version": "v1", "aceptada": True}},
]

for d in decl_tests:
    payload = {**base, **d}
    r = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=payload)
    if "DECLARACION_REQUERIDA" not in r.text:
        print(f"[SUCCESS!] {d} -> Status {r.status_code}: {r.text}")
    else:
        print(f"[FAIL] {d} -> {r.text}")
