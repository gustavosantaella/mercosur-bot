import requests

r = requests.get("https://clientsapp.mercosur.com.ve/_next/static/chunks/webpack-5a39f769031b6642.js")
print(r.text)
