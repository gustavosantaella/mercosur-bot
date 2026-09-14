import requests
import re

# Fetch main html and page links
r = requests.get("https://clientsapp.mercosur.com.ve/")
html = r.text

# Find all script src links in html
scripts = re.findall(r'src="([^"]+)"', html)
print("Scripts:", scripts)

for s in scripts:
    url = "https://clientsapp.mercosur.com.ve" + s if s.startswith("/") else s
    res = requests.get(url)
    t = res.text
    if "/ordenes" in t or "ordenes" in t:
        print(f"Match in {s}:")
        for match in re.finditer(r'.{0,100}/ordenes.{0,100}', t):
            print("  ", match.group(0))
