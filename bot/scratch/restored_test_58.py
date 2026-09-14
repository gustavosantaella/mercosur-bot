import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

# Send a payload containing all potential declaration fields set to True / 1 / "SI" / "true"
super_payload = {
    "cuenta_id": 4391,
    "cartera_id": 4391,
    "tipo": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
    "clave_operaciones": "131100",
    
    # Booleans
    "declaracion_jurada": True,
    "acepta_declaracion_jurada": True,
    "declaracion_origen_fondos": True,
    "acepta_declaracion": True,
    "declaracion": True,
    "declaracion_aceptada": True,
    "aceptar_declaracion": True,
    "declaracion_jurada_aceptada": True,
    "acepta_terminos": True,
    "terminos_aceptados": True,
    "origen_fondos": True,
    "declaracion_origen_recursos": True,
    "declaracionJurada": True,
    "aceptaDeclaracionJurada": True,
    
    # Strings
    "declaracion_jurada_str": "SI",
    "declaracion_jurada_txt": "Acepto",

    # Nested
    "declaracion_info": {"jurada": True, "origen_fondos": True, "acepta": True}
}

r = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=super_payload)
print("Super payload status:", r.status_code)
print("Super payload response:", r.text)
