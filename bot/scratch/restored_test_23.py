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

keys_to_test = [
    "declaracion_jurada",
    "declaracionJurada",
    "declaracion",
    "declaracion_origen_fondos",
    "acepta_declaracion",
    "acepta_declaracion_jurada",
    "aceptaDeclaracionJurada",
    "aceptar_declaracion",
    "declaracion_fondos",
    "declaracion_origen",
    "origen_fondos",
    "origen_fondos_declaracion",
    "aceptado",
    "acepta",
    "jurada",
    "declaracion_jurada_aceptada",
    "declaracionJuradaAceptada",
    "terminos",
    "acepta_terminos",
    "declaracion_origen_recursos",
    "origen_recursos"
]

for key in keys_to_test:
    # Test boolean True
    p1 = {**base, key: True}
    r1 = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=p1)
    
    # Test string "1" or "true" or "SI"
    p2 = {**base, key: "1"}
    r2 = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=p2)
    
    p3 = {**base, key: 1}
    r3 = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=p3)

    print(f"Key '{key}': True -> {r1.text} | '1' -> {r2.text} | 1 -> {r3.text}")
