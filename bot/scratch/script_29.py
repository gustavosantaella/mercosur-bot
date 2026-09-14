import requests
import re

url = 'https://clientsapp.mercosur.com.ve/'
r = requests.get(url)
js_files = re.findall(r'src="([^"]+\.js)"', r.text) + re.findall(r'href="([^"]+\.js)"', r.text)
print('JS files found:', js_files)

for js in js_files:
    if not js.startswith('http'):
        js_url = 'https://clientsapp.mercosur.com.ve/' + js.lstrip('/')
    else:
        js_url = js
    print('Fetching:', js_url)
    res = requests.get(js_url)
    if 'DECLARACION' in res.text.upper() or 'ORDENES' in res.text.upper():
        matches = re.findall(r'.{0,100}declaracion.{0,100}', res.text, re.IGNORECASE)
        print(f'Matches in {js}:', len(matches))
        for m in matches[:10]:
            print('   ', m)
