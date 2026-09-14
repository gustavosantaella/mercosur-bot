import requests
import re

r = requests.get("https://clientsapp.mercosur.com.ve/_next/static/chunks/webpack-5a39f769031b6642.js")
text = r.text

print("webpack JS length:", len(text))
# Webpack chunk hash mapping usually looks like {6609:"018de208...", 9060:"88def..."}
hashes = re.findall(r'(\d+):"([a-f0-9]+)"', text)
print("Found chunk hashes:", len(hashes), hashes)

for chunk_id, chunk_hash in hashes:
    url = f"https://clientsapp.mercosur.com.ve/_next/static/chunks/{chunk_id}-{chunk_hash}.js"
    print(f"Fetching chunk {chunk_id}: {url}")
    res = requests.get(url)
    if "declaracion" in res.text.lower() or "orden" in res.text.lower():
        print(f"  FOUND IN {chunk_id}-{chunk_hash}.js !")
        matches = re.finditer(r'.{0,100}(?:declaracion|clave_operaciones|ordenes).{0,100}', res.text, re.IGNORECASE)
        for i, m in enumerate(matches):
            if i < 15:
                print(f"    MATCH: {m.group(0)}")
