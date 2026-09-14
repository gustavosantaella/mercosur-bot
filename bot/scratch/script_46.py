import requests
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

# Send empty payload to see backend validation response
r = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json={})
print("Empty body response:", r.status_code, r.text)

# Send body with just cuenta_id and cartera_id
r2 = client.session.post("https://cm.mercosur.com.ve/portal/ordenes", json={"cuenta_id": 4391, "cartera_id": 4391})
print("Cuenta/cartera response:", r2.status_code, r2.text)
