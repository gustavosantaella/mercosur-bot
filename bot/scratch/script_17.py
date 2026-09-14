import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base = "https://cm.mercosur.com.ve/portal"
cart_res = client.session.get(f"{base}/carrito").json()
cart_id = cart_res.get("data", {}).get("carrito", {}).get("id", "234")

print(f"Cart ID: {cart_id}")

endpoints = [
    f"{base}/carrito/items",
    f"{base}/carrito/item",
    f"{base}/carrito/{cart_id}/items",
    f"{base}/carrito/{cart_id}/item",
    f"{base}/carrito/{cart_id}/procesar",
    f"{base}/carrito/{cart_id}/ejecutar",
    f"{base}/carrito/{cart_id}/confirmar",
    f"{base}/carrito/ejecutar",
]

for ep in endpoints:
    r_get = client.session.get(ep)
    print(f"GET {ep} -> Status {r_get.status_code}: {r_get.text[:150]}")
    r_post = client.session.post(ep, json={"clave_operaciones": "131100"})
    print(f"POST {ep} -> Status {r_post.status_code}: {r_post.text[:150]}")
