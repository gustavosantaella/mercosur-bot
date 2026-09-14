import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal/declaracion-jurada"

endpoints_and_payloads = [
    (base, {"version": "v1"}),
    (base, {"version": "v1", "aceptada": True}),
    (base, {"version": "v1", "acepta": True}),
    (base, {"version": "v1", "declaracion": True}),
    (base, {"version": "v1", "declaracion_jurada": True}),
    (base + "/aceptar", {"version": "v1"}),
    (base + "/aceptar", {"version": "v1", "aceptada": True}),
    (base + "/acepto", {"version": "v1"}),
    (base + "/firmar", {"version": "v1"}),
    ("https://cm.mercosur.com.ve/portal/declaraciones", {"version": "v1"}),
]

for url, p in endpoints_and_payloads:
    r = client.session.post(url, json=p)
    print(f"POST {url} with {p} -> Status {r.status_code}: {r.text}")
