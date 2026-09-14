import requests
import re

url = 'https://clientsapp.mercosur.com.ve/'
r = requests.get(url)
build_id_match = re.search(r'/_next/static/([^/]+)/_buildManifest\.js', r.text)

if build_id_match:
    build_id = build_id_match.group(1)
    manifest_url = f'https://clientsapp.mercosur.com.ve/_next/static/{build_id}/_buildManifest.js'
    print('Manifest URL:', manifest_url)
    manifest_res = requests.get(manifest_url)
    print(manifest_res.text[:2000])
else:
    print('No build manifest found, searching HTML for buildId or route chunks...')
    print(re.findall(r'/_next/static/[^\"]+', r.text))
