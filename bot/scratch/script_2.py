import requests

r = requests.get("https://clientsapp.mercosur.com.ve/_next/static/chunks/2635-c79bd66db1d7072e.js")
print(r.text)
