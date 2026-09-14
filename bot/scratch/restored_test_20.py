import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal"
candidates = [
    "/declaracion/vigente",
    "/declaracion/activa",
    "/declaraciones/vigente",
    "/declaracion-jurada/vigente",
    "/declaraciones",
    "/declaracion",
    "/ordenes/declaracion",
    "/ordenes/declaracion-jurada",
    "/ordenes/declaracion_jurada",
    "/mercado/declaracion",
    "/configuracion",
    "/parametros",
    "/sistema/declaracion",
]

for c in candidates:
    r = client.session.get(base + c)
    if r.status_code != 404:
        print(f"FOUND! GET {c} -> Status {r.status_code}: {r.text}")
    else:
        print(f"404 {c}")
