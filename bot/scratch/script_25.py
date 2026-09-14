import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal"

endpoints = [
    "/me",
    "/declaracion-jurada",
    "/declaracion-jurada/aceptar",
    "/declaracion-jurada/vigente",
    "/declaracion",
    "/declaraciones",
    "/perfil",
    "/cliente",
    "/usuario",
    "/declaracion_jurada",
]

payloads = [
    {"declaracion_jurada": True},
    {"acepta_declaracion_jurada": True},
    {"version": "v1", "aceptada": True},
    {"declaracion": True},
]

for ep in endpoints:
    for p in payloads:
        url = base + ep
        r_post = client.session.post(url, json=p)
        r_put = client.session.put(url, json=p)
        
        if r_post.status_code != 404:
            print(f"POST {ep} -> Status {r_post.status_code}: {r_post.text[:200]}")
        if r_put.status_code != 404:
            print(f"PUT {ep} -> Status {r_put.status_code}: {r_put.text[:200]}")
