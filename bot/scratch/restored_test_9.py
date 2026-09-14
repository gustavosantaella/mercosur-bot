import requests
import re

url = "https://clientsapp.mercosur.com.ve/"
r = requests.get(url)
text = r.text

# Find all chunk names in text
chunks = re.findall(r'"static/chunks/[^"]+"', text)
print("Chunks found in html:", len(chunks), chunks)

# Also check layout or main JS for page routes
for script_path in re.findall(r'/_next/static/chunks/[^"]+\.js', text):
    full_url = "https://clientsapp.mercosur.com.ve" + script_path
    print("Inspecting:", script_path)
    res = requests.get(full_url)
    if "DECLARACION" in res.text.upper():
        print("  --> FOUND DECLARACION IN", script_path)
        for match in re.finditer(r'.{0,100}declaracion.{0,100}', res.text, re.IGNORECASE):
            print("     MATCH:", match.group(0))

    if "ordenes" in res.text.lower():
        print("  --> FOUND ordenes IN", script_path)
        for match in re.finditer(r'.{0,100}/portal/ordenes.{0,100}', res.text, re.IGNORECASE):
            print("     MATCH:", match.group(0))
