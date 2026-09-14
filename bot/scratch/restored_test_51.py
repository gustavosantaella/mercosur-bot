import requests
import re

# Fetch main HTML and inspect Next.js inline scripts for page routes or chunk mappings
r = requests.get("https://clientsapp.mercosur.com.ve/")
html = r.text

# Find scripts
scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
print("Scripts in HTML:", scripts)

# Search inside 8928 or other chunks for API endpoints or DECLARACION
for s in scripts:
    url = "https://clientsapp.mercosur.com.ve" + s if s.startswith("/") else s
    res = requests.get(url)
    text = res.text
    if "declaracion" in text.lower():
        print(f"FOUND 'declaracion' in script {s}")
        for match in re.finditer(r'.{0,150}declaracion.{0,150}', text, re.IGNORECASE):
            print(" MATCH:", match.group(0))

    if "ordenes" in text.lower():
        print(f"FOUND 'ordenes' in script {s}")
        for match in re.finditer(r'.{0,100}/portal/ordenes.{0,100}', text, re.IGNORECASE):
            print(" ORDENES MATCH:", match.group(0))
