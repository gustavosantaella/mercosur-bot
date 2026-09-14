import json
from src.client.mercosur_client import MercosurClient

client = MercosurClient()
client.login()

r = client.session.get("https://cm.mercosur.com.ve/portal/ordenes")
orders = r.json().get("data", [])
print(f"Total past orders: {len(orders)}")
if orders:
    print("Most recent order sample:")
    print(json.dumps(orders[0], indent=2))
    
    # Try GET /ordenes/{id} for the first order
    order_id = orders[0].get("id")
    if order_id:
        r2 = client.session.get(f"https://cm.mercosur.com.ve/portal/ordenes/{order_id}")
        print(f"GET /ordenes/{order_id} -> {r2.status_code}")
        print(json.dumps(r2.json(), indent=2))
