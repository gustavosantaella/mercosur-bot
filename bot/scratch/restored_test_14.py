import json
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

print("User Data:", json.dumps(client.user_data, indent=2))
