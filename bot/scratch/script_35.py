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
    "clave_operaciones": "131100"
}

# Test different payload structures:
tests = [
    # 1. Strings
    ("declaracion_jurada string SI", {**base, "declaracion_jurada": "SI"}),
    ("declaracion_jurada string S", {**base, "declaracion_jurada": "S"}),
    ("declaracion_jurada string true", {**base, "declaracion_jurada": "true"}),
    ("declaracion_jurada string TRUE", {**base, "declaracion_jurada": "TRUE"}),
    ("declaracion_jurada int 1", {**base, "declaracion_jurada": 1}),
    
    # 2. Other field names
    ("acepta_declaracion_jurada", {**base, "acepta_declaracion_jurada": True}),
    ("acepta_declaracion_jurada 1", {**base, "acepta_declaracion_jurada": 1}),
    ("acepta_declaracion_jurada SI", {**base, "acepta_declaracion_jurada": "SI"}),
    ("declaracion_jurada_aceptada", {**base, "declaracion_jurada_aceptada": True}),
    ("acepta_declaracion", {**base, "acepta_declaracion": True}),
    ("declaracion_origen_fondos", {**base, "declaracion_origen_fondos": True}),
    ("declaracion_origen_fondos SI", {**base, "declaracion_origen_fondos": "SI"}),

    # 3. Object / Dict
    ("declaracion object", {**base, "declaracion": {"aceptada": True, "jurada": True}}),
    ("declaracion_jurada object", {**base, "declaracion_jurada": {"acepta": True}}),

    # 4. Spanish variations
    ("declaracionJurada Aceptada", {**base, "declaracionJuradaAceptada": True}),
    ("aceptaDeclaracionJurada", {**base, "aceptaDeclaracionJurada": True}),
    ("declaracionJurada", {**base, "declaracionJurada": True}),
    ("jurada", {**base, "jurada": True}),
    ("declaracion_fondos", {**base, "declaracion_fondos": True}),
    ("acepta_declaracion_origen_fondos", {**base, "acepta_declaracion_origen_fondos": True}),
]

for label, payload in tests:
    res = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=payload)
    if "DECLARACION_REQUERIDA" not in res.text:
        print(f"[FOUND MATCH!] {label} -> Status {res.status_code}: {res.text}")
    else:
        print(f"[NO MATCH] {label} -> {res.text}")
