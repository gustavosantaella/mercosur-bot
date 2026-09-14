import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

balances = client.get_balances()
account_id = balances.get("account_id", 4391)

single_item = {
    "cuenta_id": account_id,
    "cartera_id": account_id,
    "tipo": "COMPRA",
    "tipo_operacion": "COMPRA",
    "cod_simb": "BNC",
    "cantidad": 1,
    "precio": 235.0,
    "tipo_precio": "LIMIT",
}

# Test various batch/cart structures on POST /portal/ordenes:
payload_variations = [
    # Array of orders
    [ {**single_item, "declaracion_jurada": True, "clave_operaciones": "131100"} ],
    
    # Dict with "ordenes" array + root declaration & PIN
    {
        "declaracion_jurada": True,
        "clave_operaciones": "131100",
        "ordenes": [ single_item ]
    },
    
    # Dict with "items" array
    {
        "declaracion_jurada": True,
        "clave_operaciones": "131100",
        "items": [ single_item ]
    },

    # Dict with "ordenes" array where each order has declaracion_jurada & clave_operaciones
    {
        "clave_operaciones": "131100",
        "ordenes": [ {**single_item, "declaracion_jurada": True} ]
    },

    # Root acepto_declaracion
    {
        "acepta_declaracion_jurada": True,
        "declaracion_jurada": True,
        "clave_operaciones": "131100",
        "ordenes": [ single_item ]
    }
]

for i, p in enumerate(payload_variations):
    r = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json=p)
    print(f"\nVariation {i}: Status {r.status_code}")
    print("Response:", r.text)
