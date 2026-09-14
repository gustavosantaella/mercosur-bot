import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

base_url = "https://cm.mercosur.com.ve/portal"
paths = [
    "/me",
    "/perfil",
    "/cliente",
    "/cuentas",
    "/carteras",
    "/saldos",
    "/declaracion",
    "/declaraciones",
    "/declaracion-jurada",
    "/declaracion_jurada",
    "/origen-fondos",
    "/origen_fondos",
    "/terminos",
    "/documentos",
    "/configuracion",
    "/usuario",
    "/ordenes",
    "/mercado/dashboard/cotizaciones",
    "/notificaciones",
    "/mensajes",
    "/alertas",
]

for p in paths:
    r = client.session.get(base_url + p)
    print(f"GET {p} -> Status {r.status_code}: {r.text[:150]}")
