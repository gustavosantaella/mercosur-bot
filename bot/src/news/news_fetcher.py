import socket
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

_CONNECTIVITY_HOST = "8.8.8.8"
_CONNECTIVITY_PORT = 53
_CONNECTIVITY_TIMEOUT = 3

def _has_internet() -> bool:
    """Verifica si hay conexión a Internet resolviendo contra Google DNS."""
    try:
        socket.setdefaulttimeout(_CONNECTIVITY_TIMEOUT)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((_CONNECTIVITY_HOST, _CONNECTIVITY_PORT))
        return True
    except Exception:
        return False

class NewsFetcher:
    def __init__(self):
        self.feeds = [
            {
                "name": "Bolsa de Valores de Caracas",
                "url": "https://www.bolsadecaracas.com/feed/"
            },
            {
                "name": "Mercosur Casa de Bolsa",
                "url": "https://mercosurcb.com/feed/"
            }
        ]

    def fetch_latest_news(self) -> List[Dict[str, Any]]:
        if not _has_internet():
            return []

        all_news = []
        for feed_info in self.feeds:
            if isinstance(feed_info, dict):
                feed_name = feed_info.get("name", "Fuente Desconocida")
                feed_url = feed_info.get("url", "")
            elif isinstance(feed_info, (list, tuple)) and len(feed_info) >= 2:
                feed_name = str(feed_info[0])
                feed_url = str(feed_info[1])
            elif isinstance(feed_info, str):
                feed_name = feed_info
                feed_url = feed_info
            else:
                continue

            if not feed_url or not feed_url.startswith("http"):
                continue

            try:
                req = urllib.request.Request(
                    feed_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    xml_data = response.read()
                    root = ET.fromstring(xml_data)
                    
                    for item in root.findall('.//item'):
                        title = item.findtext('title', default='Sin título')
                        link = item.findtext('link', default='')
                        pub_date = item.findtext('pubDate', default='')
                        
                        all_news.append({
                            "source": feed_name,
                            "title": title.strip(),
                            "link": link.strip(),
                            "pub_date": pub_date.strip()
                        })
            except Exception:
                pass

        return all_news
