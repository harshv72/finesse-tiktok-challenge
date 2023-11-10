import json
import random
import requests
from bs4 import BeautifulSoup
from collections import namedtuple
from urllib.parse import urlencode, quote
from playwright.sync_api import sync_playwright

# Browser session state
session = namedtuple('session', ['browser', 'context', 'page', 'info'])

# Default Configs
configs = {
    "Lang": "en",
    "Locale": "en-US",
    "TimeZone": "America/Chicago",
    "DefaultURL": "https://www.tiktok.com/@redbull?lang=en",
    "RndDeviceID": str(random.randint(10 ** 18, 10 ** 19 - 1)),
    "UserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
}

# Common Headers for APIs
headers = {
    "Origin": "https://www.tiktok.com/",
    "Referer": "https://www.tiktok.com/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Authority': 'www.tiktok.com',
    "User-Agent": configs["UserAgent"],
}


def get_params():
    return {
        "aid": "1988",
        "app_language": configs["Lang"],
        "app_name": "tiktok_web",
        "browser_language": session.info["browser_language"],
        "browser_name": "Mozilla",
        "browser_online": "true",
        "browser_platform": session.info["browser_platform"],
        "browser_version": session.info["user_agent"],
        "channel": "tiktok_web",
        "cookie_enabled": "true",
        "device_id": configs["RndDeviceID"],
        "device_platform": "web_pc",
        "focus_state": "true",
        "from_page": "user",
        "history_len": session.info["history"],
        "is_fullscreen": "false",
        "is_page_visible": "true",
        "language": configs["Lang"],
        "os": session.info["platform"],
        "priority_region": "",
        "referer": "",
        "region": "US",
        "screen_height": session.info["screen_height"],
        "screen_width": session.info["screen_width"],
        "tz_name": configs["TimeZone"],
        "webcast_language": configs["Lang"],
    }


def fetch_data(url, headers):
    headers_js = json.dumps(headers)
    js_fetch = f"""
        () => {{
            return new Promise((resolve, reject) => {{
                fetch('{url}', {{ method: 'GET', headers: {headers_js} }})
                    .then(response => response.json())
                    .then(data => resolve(data))
                    .catch(error => reject(error.message));
            }});
        }}
    """
    return session.page.evaluate(js_fetch)


def encode_url(base, params):
    return f"{base}?{urlencode(params, quote_via=quote)}"


# Close current browser instance
def session_close():
    if session.browser is not None:
        session.browser.close()
    exit(0)


def extract_stateinfo(content):
    soup = BeautifulSoup(content, 'html.parser')
    hydra_data = soup.find_all('script', {'id': '__UNIVERSAL_DATA_FOR_REHYDRATION__'})
    if len(hydra_data) > 0:
        js_state = hydra_data[0]
        # js_state.text.encode('utf-8').decode('unicode_escape'), Corrupts the non-Ascii characters
        unescaped = js_state.text.replace("//", "/")
        return json.loads(unescaped)
    return None


def fetch_recommenations(count=10):
    base_url = "https://www.tiktok.com/api/recommend/item_list/"

    params = get_params()
    params["from_page"] = "fyp"
    params["count"] = 30

    # Max cap for now
    if count > 100:
        count = 100

    res = []
    found = 0

    while found < count:
        result = fetch_data(encode_url(base_url, params), headers)

        if 'itemList' not in result:
            break

        for t in result.get("itemList", []):
            res.append(t)
            found += 1

        if not result.get("hasMore", False):
            return res

        count -= found

    return res[:count]


def fetch_challenge_info(challenge="fashion"):
    base_url = "https://www.tiktok.com/api/challenge/detail/"

    params = get_params()
    params["from_page"] = "hashtag"
    params["challengeName"] = challenge

    result = fetch_data(encode_url(base_url, params), headers)
    if ("challengeInfo" not in result) or result["statusCode"] != 0:
        return None

    return result["challengeInfo"]


def fetch_tags_posts(hashtag="fashion", count=30):
    tag_data = fetch_challenge_info(hashtag)

    if not tag_data or "challenge" not in tag_data:
        return None

    tag_data = tag_data["challenge"]

    base_url = "https://www.tiktok.com/api/challenge/item_list/"

    params = get_params()
    params["challengeID"] = tag_data["id"]
    params["coverFormat"] = "2"
    params["cursor"] = "0"
    params["count"] = 30

    res = []
    found = 0

    while found < count:
        result = fetch_data(encode_url(base_url, params), headers)

        if ("cursor" not in result and "itemList" not in result) or result["statusCode"] != 0:
            break

        for t in result.get("itemList", []):
            res.append(t)
            found += 1

        if not result.get("hasMore", False):
            return res

        params["cursor"] = result["cursor"]

    return res[:count]


def get_user_info(hashtag="redbull"):
    user_url = "https://www.tiktok.com/@{}".format(hashtag)

    r = requests.get(user_url, headers=headers)
    if r.status_code != 200:
        return None

    data = extract_stateinfo(r.content)
    if "__DEFAULT_SCOPE__" in data:
        data = data["__DEFAULT_SCOPE__"]
        if "webapp.user-detail" in data:
            return data["webapp.user-detail"]
    return None


if __name__ == '__main__':
    print('[=>] TikTok Fashion Scraper Starting')

    with sync_playwright() as playwright:
        mobile_device = playwright.devices['iPhone 14 Pro Max']

        session.browser = playwright.chromium.launch(
            headless=True,
            args=["--user-agent={}".format(configs["UserAgent"])],
            ignore_default_args=["--mute-audio", "--hide-scrollbars"],
        )

        session.context = session.browser.new_context(
            **mobile_device,
            bypass_csp=True,
            locale=configs["Locale"],
            timezone_id=configs["TimeZone"],
        )

        session.page = session.context.new_page()
        session.page.goto(configs["DefaultURL"], wait_until="networkidle")
        session.info = session.page.evaluate("""() => {
          return {
            platform: window.navigator.platform,
            deviceScaleFactor: window.devicePixelRatio,
            user_agent: window.navigator.userAgent,
            screen_width: window.screen.width,
            screen_height: window.screen.height,
            history: window.history.length,
            browser_language: window.navigator.language,
            browser_platform: window.navigator.platform,
            browser_name: window.navigator.appCodeName,
            browser_version: window.navigator.appVersion,
          };
        }""")

        # fashion_data = fetch_tags_posts("fashion", count=30)
        # if not fashion_data:
        #     print("[!] Failed to get to Fashion Tag Posts")
        #     session_close()
        #
        # count = 0
        # for rec in fashion_data:
        #     print(f'[=>] Post {count + 1}: {rec["id"]}')
        #     print(f'[*] Description: {rec["desc"]}')
        #     print(f'[*] Play Count: {rec["stats"]["playCount"]}')
        #     print(f'[*] Share Count: {rec["stats"]["shareCount"]}')
        #     print(f'[*] Comment Count: {rec["stats"]["commentCount"]}')
        #     print(f'[*] Author: {rec["author"]["nickname"]}')
        #     print()
        #     count += 1

        # result = fetch_challenge()
        # print(result)

        # recomd = fetch_recommenations(10)
        # if not recomd:
        #     print("[!] Failed to get to Recommended Posts")
        #     session_close()
        #
        # count = 0
        # for rec in recomd:
        #     print(f'[=>] Post {count + 1}: {rec["id"]}')
        #     print(f'[*] Description: {rec["desc"]}')
        #     print(f'[*] Play Count: {rec["stats"]["playCount"]}')
        #     print(f'[*] Share Count: {rec["stats"]["shareCount"]}')
        #     print(f'[*] Comment Count: {rec["stats"]["commentCount"]}')
        #     print(f'[*] Author: {rec["author"]["nickname"]}')
        #     print()
        #     count += 1

        session.browser.close()

    print("[=>] TikTok Fashion Scraper Stopped")