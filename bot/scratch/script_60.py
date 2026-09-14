import requests
import re

# Fetch main login page HTML to get buildId and static paths
r = requests.get("https://clientsapp.mercosur.com.ve/login")
html = r.text

js_paths = set(re.findall(r'/_next/static/[^"\']+\.js', html))
print(f"Discovered {len(js_paths)} JS paths directly in login HTML.")

# Download each JS path and search
for p in sorted(js_paths):
    url = "https://clientsapp.mercosur.com.ve" + p
    res = requests.get(url)
    text = res.text
    if "DECLARACION_REQUERIDA" in text or "declaración jurada" in text.lower() or "declaracion_jurada" in text.lower():
        print(f"\n================ FOUND IN {p} ================")
        matches = re.finditer(r'.{0,150}(?:DECLARACION_REQUERIDA|declaracion_jurada|declaracion).{0,150}', text, re.IGNORECASE)
        for m in matches:
            print("  MATCH:", m.group(0))
