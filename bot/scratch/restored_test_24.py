import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

endpoints = [
    "https://cm.mercosur.com.ve/portal/declaracion",
    "https://cm.mercosur.com.ve/portal/declaraciones",
    "https://cm.mercosur.com.ve/portal/declaracion-jurada",
    "https://cm.mercosur.com.ve/portal/cliente",
    "https://cm.mercosur.com.ve/portal/cliente/declaracion",
    "https://cm.mercosur.com.ve/portal/perfil",
    "https://cm.mercosur.com.ve/portal/ordenes/declaracion",
]

for ep in endpoints:
    r = client.session.get(ep)
    print(f"GET {ep}: Status {r.status_code} -> {r.text[:200]}")
    r_post = client.session.post(ep, json={"declaracion": True, "acepta": True})
    print(f"POST {ep}: Status {r_post.status_code} -> {r_post.text[:200]}")
