import requests
import re

# Fetch main html
r = requests.get("https://clientsapp.mercosur.com.ve/login")
js_paths = re.findall(r'/_next/static/[^"\']+\.js', r.text)

# Also check for chunk lists inside js files
found_urls = set(js_paths)
print("Initial JS paths:", len(found_urls))

# Download each and look for DECLARACION or /ordenes or field names
for path in list(found_urls):
    url = "https://clientsapp.mercosur.com.ve" + path
    try:
        res = requests.get(url, timeout=5)
        text = res.text
        # Find any other chunk files listed in this JS
        more_chunks = re.findall(r'static/chunks/[^"\']+\.js', text)
        for mc in more_chunks:
            full_mc = "/_next/" + mc
            if full_mc not in found_urls:
                found_urls.add(full_mc)
                print(" Found sub-chunk:", full_mc)
    except Exception as e:
        print("Error fetching:", url, e)

print(f"Total discovered JS files: {len(found_urls)}")

for path in sorted(found_urls):
    url = "https://clientsapp.mercosur.com.ve" + path
    try:
        res = requests.get(url, timeout=5)
        text = res.text
        if "declaracion" in text.lower() or "ordenes" in text.lower() or "clave_operaciones" in text.lower():
            print(f"\n====================\nFILE: {path}\n====================")
            matches = re.finditer(r'.{0,100}(?:declaracion|clave_operaciones|ordenes).{0,100}', text, re.IGNORECASE)
            for i, m in enumerate(matches):
                if i < 15:
                    print(f"  {m.group(0)}")
    except Exception as e:
        pass
