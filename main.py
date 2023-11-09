import json

import requests
from bs4 import BeautifulSoup

# Request object with Session maintained
session = requests.Session()

# Common Headers for Session
headers = {
    "Referer": "https://www.tiktok.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
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


def fetch_recommenations(count=10):
    url = ("https://www.tiktok.com/api/recommend/item_list/?aid=1988&app_language=en&app_name=tiktok_web"
           "&browser_language=en-US&browser_name=Mozilla&browser_online=true&browser_platform=MacIntel"
           "&browser_version=5.0%20%28iPhone%3B%20CPU%20iPhone%20OS%2016_6%20like%20Mac%20OS%20X%29%20AppleWebKit%2F60"
           "5.1.15%20%28KHTML%2C%20like%20Gecko%29%20Version%2F16.6%20Mobile%2F15E148%20Safari%2F604.1"
           "&channel=tiktok_web&cookie_enabled=true&count=9&coverFormat=0&device_id=7300197118059234859"
           "&device_platform=web_mobile&focus_state=true&from_page=fyp&history_len=6&isNonPersonalized=false"
           "&is_fullscreen=false&is_page_visible=true&os=ios&priority_region=&pullType=1&referer=&region=US"
           "&screen_height=932&screen_width=430&tz_name=Asia%2FCalcutta&webcast_language=en"
           "&msToken=lZLoLEEK53Wl91zNeiFDUJ2k9O354VG_svE3qtWERQqSNCgMtk0jIFM2JZvLm_vV8m_VKYmnWx-GnN9unfzicMnJ3"
           "ApvGB_c6UCmxj5piLFy4aDDVHtUhcb3UDqeCilPMANkt5dx9eRGTrnp2rI="
           "&X-Bogus=DFSzsIVuTEiANn7BtFznfU9WcBJz"
           "&_signature=_02B4Z6wo00001O1TKPwAAIDA7VMo.941d5ztUSxAAF4h50")

    # r = session.get(url, headers=headers)
    # if r.status_code != 200:
    #     return None

    # print(r.content)

    # result = r.json()
    # if 'itemList' not in result:
    #     return None

    res = []
    first = True

    if count < 100:
        realCount = count
    else:
        realCount = 100

    while len(res) < count:
        r = session.get(url.format(realCount), headers=headers)
        if r.status_code != 200:
            break

        result = r.json()
        if 'itemList' not in result:
            break

        for t in result.get("itemList", []):
            res.append(t)

        if not result.get("hasMore", False) and not first:
            return res[:count]

        realCount = count - len(res)

        first = False

    return res[:count]


if __name__ == '__main__':
    print('[=>] TikTok Fashion Scraper Starting')

    # Starts with origin url to load important cookies
    r = session.get("https://m.tiktok.com/", headers=headers, allow_redirects=True)
    if r.status_code != 200:
        print("[!] Failed to Connect to Origin")
        exit(0)
    print(r.cookies)

    recomd = fetch_recommenations(10)
    if not recomd:
        print("[!] Failed to get to Recommended Posts")
        exit(0)

    count = 0
    for rec in recomd:
        print(f'[=>] Post {count + 1}: {rec["id"]}')
        print(f'[*] Description: {rec["desc"]}')
        print(f'[*] Play Count: {rec["stats"]["playCount"]}')
        print(f'[*] Share Count: {rec["stats"]["shareCount"]}')
        print(f'[*] Comment Count: {rec["stats"]["commentCount"]}')
        print(f'[*] Author: {rec["author"]["nickname"]}')
        print()
        count += 1
    print("[=>] TikTok Fashion Scraper Stopped")