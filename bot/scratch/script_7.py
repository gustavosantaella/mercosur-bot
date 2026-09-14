import requests
import re

chunk_urls = [
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/4bd1b696-e5d7c65570c947b7.js",
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/8928-776ad121bed8a4d3.js",
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/6609-018de208ab26701b.js",
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/9060-88def9b2b4acd932.js",
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/8500-98e13bcce54aa7a0.js",
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/5772-b269aad91334bb01.js",
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/6766-4d5dfbdd0bcd7970.js",
    "https://clientsapp.mercosur.com.ve/_next/static/chunks/2635-c79bd66db1d7072e.js",
]

for url in chunk_urls:
    res = requests.get(url)
    text = res.text
    print(f"\n====================\nURL: {url} (Length: {len(text)})\n====================")
    
    # Search for declaracion, ordenes, or post requests
    for match in re.finditer(r'.{0,100}(?:declaracion|declaración|ordenes|POST|orden|jurada).{0,100}', text, re.IGNORECASE):
        print("  MATCH:", match.group(0))
