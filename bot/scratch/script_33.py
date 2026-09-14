import requests
import re

routes = [
    "app/dashboard/page",
    "app/dashboard/ordenes/page",
    "app/dashboard/mercado/page",
    "app/ordenes/page",
    "app/mercado/page",
    "app/(dashboard)/ordenes/page",
    "app/(dashboard)/mercado/page",
    "app/(dashboard)/dashboard/page",
]

# Let's search inside chunk main-app-275be54ab3715b12.js for app page chunk paths
r = requests.get("https://clientsapp.mercosur.com.ve/_next/static/chunks/main-app-275be54ab3715b12.js")
print("main-app length:", len(r.text))

# Search for "app/" or "chunks/app"
app_chunks = set(re.findall(r'app/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*', r.text))
print("App routes/chunks referenced in main-app:", app_chunks)

# Also check layout chunk
r2 = requests.get("https://clientsapp.mercosur.com.ve/_next/static/chunks/app/layout-fc4fd33c998bd2fa.js")
app_chunks2 = set(re.findall(r'app/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*', r2.text))
print("App routes referenced in layout:", app_chunks2)
