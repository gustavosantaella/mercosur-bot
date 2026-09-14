import requests
import re
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

# Test fetching client app pages authenticated
headers = {
    "Authorization": f"Bearer {client.token}",
    "Cookie": f"token={client.token}"
}

pages = [
    "https://clientsapp.mercosur.com.ve/ordenes",
    "https://clientsapp.mercosur.com.ve/dashboard",
    "https://clientsapp.mercosur.com.ve/mercado",
    "https://clientsapp.mercosur.com.ve/declaracion",
]

for p in pages:
    res = requests.get(p, headers=headers)
    print(f"Page {p}: Status {res.status_code}, Length {len(res.text)}")
    # Find chunk URLs in response
    chunks = set(re.findall(r'/_next/static/chunks/[^"\'\s]+\.js', res.text))
    print(f"  Chunks found ({len(chunks)}):", list(chunks)[:5])
