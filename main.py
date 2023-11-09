import json

import requests
from bs4 import BeautifulSoup

# Request object with Session maintained
session = requests.Session()

# Common Headers for Session
headers = {
    "Referer": "https://www.tiktok.com/",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
}


def extract_stateinfo(content):
    soup = BeautifulSoup(content, 'html.parser')
    hydra_data = soup.find_all('script', {'id': '__UNIVERSAL_DATA_FOR_REHYDRATION__'})
    if len(hydra_data) > 0:
        js_state = hydra_data[0]
        unescaped = js_state.text.encode('utf-8').decode('unicode_escape')
        return json.loads(unescaped)
    return None


if __name__ == '__main__':
    print('[=>] TikTok Fashion Scraper Starting')
    r = session.get("https://www.tiktok.com/", headers=headers, allow_redirects=True)
    if r.status_code != 200:
        print("[!] Failed to Connect to Origin")
        exit(0)
    print("[=>] TikTok Fashion Scraper Stopped")