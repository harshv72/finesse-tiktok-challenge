import json
import random
import requests
import pandas as pd
from datetime import datetime
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
    "RndDeviceID": str(random.randint(10 ** 18, 10 ** 19 - 1)),
    "DefaultURL": "https://www.tiktok.com/@redbull/video/7285391124246646049",
    # "UserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.28 Safari/537.36 Edg/120.0.6099.28",
    # "UserAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "UserAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
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
                    .then(response => response.text())
                    .then(data => resolve(data))
                    .catch(error => reject(error.message));
            }});
        }}
    """
    result = session.page.evaluate(js_fetch)
    try:
        return json.loads(result)
    except ValueError as e:
        return result


def encode_url(base, params):
    return f"{base}?{urlencode(params, quote_via=quote)}"


# Close current browser instance
def session_close():
    if session.browser is not None:
        session.browser.close()
    exit(0)


def extract_stateinfo(content):
    soup = BeautifulSoup(content, 'html.parser')
    res = {}
    sigi_data = soup.find_all('script', {'id': 'SIGI_STATE'})
    if len(sigi_data) > 0:
        js_state = sigi_data[0]
        unescaped = js_state.text.replace("//", "/")
        res.update(json.loads(unescaped))
    hydra_data = soup.find_all('script', {'id': '__UNIVERSAL_DATA_FOR_REHYDRATION__'})
    if len(hydra_data) > 0:
        js_state = hydra_data[0]
        # js_state.text.encode('utf-8').decode('unicode_escape'), Corrupts the non-Ascii characters
        unescaped = js_state.text.replace("//", "/")
        unescaped = json.loads(unescaped)
        if "__DEFAULT_SCOPE__" in unescaped:
            res.update(unescaped)
    return res


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
    if "webapp.user-detail" in data:
        return data["webapp.user-detail"]
    return None


def get_comments_info(user="redbull", post="7285391124246646049"):
    post_url = "https://www.tiktok.com/@{}/video/{}".format(user, post)

    r = requests.get(post_url, headers=headers)
    if r.status_code != 200:
        return None

    data = extract_stateinfo(r.content)
    if "MobileSharingComment" in data:
        return data["MobileSharingComment"]
    return None


def fetch_search_suggest(keyword="fashion"):
    base_url = "https://www.tiktok.com/api/search/general/sug/"

    params = get_params()
    params["from_page"] = "search"
    params["keyword"] = keyword

    result = fetch_data(encode_url(base_url, params), headers)
    if ("sug_list" not in result) or result["status_code"] != 0:
        return None

    return result["sug_list"]


def fetch_search(keyword="fashion", count=10):
    obj_type = "user"
    base_url = f"https://www.tiktok.com/api/search/{obj_type}/full/"

    params = get_params()
    params["cursor"] = "0"
    params["count"] = 20
    params["from_page"] = "search"
    params["keyword"] = keyword
    params["root_referer"] = configs["DefaultURL"]
    params["web_search_code"] = """{"tiktok":{"client_params_x":{"search_engine":{"ies_mt_user_live_video_card_use_libra":1,"mt_search_general_user_live_card":1}},"search_server":{}}}"""

    res = []
    found = 0

    while found < count:
        result = fetch_data(encode_url(base_url, params), headers)
        print(result)

        if ("cursor" not in result and "user_list" not in result) or result["statusCode"] != 0:
            break

        for t in result.get("user_list", []):
            res.append(t)
            found += 1

        if not result.get("hasMore", False):
            return res

        params["cursor"] = result["cursor"]

    return res[:count]


def fetch_post_comments(post_id="7198199504405843205", count=10):
    base_url = f"https://www.tiktok.com/api/comment/list/"

    params = get_params()
    params["cursor"] = "0"
    params["from_page"] = "video"
    params["fromWeb"] = "1"
    params["app_language"] = "ja-JP"
    params["current_region"] = "JP"
    params["aweme_id"] = post_id
    params["is_non_personalized"] = "false"
    params["enter_from"] = "tiktok_web"

    res = []
    found = 0

    while found < count:
        result = fetch_data(encode_url(base_url, params), headers)
        print(result)

        if ("cursor" not in result and "comments" not in result) or result["total"] < 1:
            break

        for t in result.get("comments", []):
            res.append(t)
            found += 1

        if not result.get("hasMore", False):
            return res

        params["cursor"] = result["cursor"]

    return res[:count]


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

        cookies = session.context.cookies()
        cookies = {cookie["name"]: cookie["value"] for cookie in cookies}
        print("[*] Cookies: ", cookies)

        # comments = get_comments_info()
        # if not comments:
        #     print("[!] Failed to get to Comments for Post")
        #     session_close()
        # print(comments)

        # suggest = fetch_search_suggest("fashion")
        # if not suggest:
        #     print("[!] Failed to get to Fashion Search Suggestions")
        #     session_close()
        #
        # print(suggest)

        # result = fetch_post_comments("7198199504405843205", 10)
        # print(result)

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

        fashion_data = fetch_tags_posts("fashion", count=30)
        if not fashion_data:
            print("[!] Failed to get to Fashion Tag Posts")
            session_close()

        count = 0
        df_data = {
            "Post URL": [],
            "User": [],
            "Author Name": [],
            "Likes": [],
            "Views": [],
            "Shares": [],
            "Comments": [],
            "Comments Data": [],
            "Caption": [],
            "HashTags": [],
            "Music": [],
            "Date Posted": [],
            "Date Collected": [],
        }

        for rec in fashion_data:
            print(f'[=>] Post {count + 1}:')
            print(f'[*] ID: {rec["id"]}')
            desc = rec["desc"]
            hashpos = desc.find("#")
            hashtags = desc[hashpos:]
            desc = desc[:hashpos]
            print(f'[*] Caption: {desc}')
            print(f'[*] HashTags: {hashtags}')
            print(f'[*] Like Count: {rec["stats"]["diggCount"]}')
            print(f'[*] View Count: {rec["stats"]["playCount"]}')
            print(f'[*] Share Count: {rec["stats"]["shareCount"]}')
            print(f'[*] Comment Count: {rec["stats"]["commentCount"]}')
            print(f'[*] Author: {rec["author"]["nickname"]}')
            print(f'[*] Author User: {rec["author"]["uniqueId"]}')
            comments_data = []
            comments = get_comments_info(rec["author"]["uniqueId"], rec["id"])
            if not comments:
                print("[!] Failed to get to Comments for Post")
            else:
                print(f'[*] Total Comments: {comments["total"]}')
                for comts in comments["comments"]:
                    comments_data.append(comts["text"])
                    print(f'[*] Comment: {comts["text"]}')
            if 'music' in rec:
                print(f'[*] Post Music: {rec["music"]["title"]}')
            print(f'[*] Post Date: {datetime.fromtimestamp(rec["createTime"])}')
            print(f'[*] Collected Date: {datetime.now()}')
            print(f'[*] Post URL: https://www.tiktok.com/@{rec["author"]["uniqueId"]}/{rec["id"]}')

            # Add to data cache
            df_data["Post URL"].append(f'https://www.tiktok.com/@{rec["author"]["uniqueId"]}/{rec["id"]}')
            df_data["User"].append(rec["author"]["uniqueId"])
            df_data["Author Name"].append(rec["author"]["nickname"])
            df_data["Likes"].append(rec["stats"]["diggCount"])
            df_data["Views"].append(rec["stats"]["playCount"])
            df_data["Shares"].append(rec["stats"]["shareCount"])
            df_data["Comments"].append(rec["stats"]["commentCount"])
            df_data["Comments Data"].append(comments_data)
            df_data["Caption"].append(desc)
            df_data["HashTags"].append(hashtags)
            df_data["Music"].append(rec["music"]["title"] if 'music' in rec else '')
            df_data["Date Posted"].append(datetime.fromtimestamp(rec["createTime"]))
            df_data["Date Collected"].append(datetime.now())

            count += 1

        # CSV export through dataframe
        df_fashion = pd.DataFrame(df_data)
        curr_timestamp = datetime.timestamp(datetime.now())
        df_fashion.to_csv(f"sample_fashion_posts-{int(curr_timestamp)}.csv", index=False)

        session.browser.close()

    print("[=>] TikTok Fashion Scraper Stopped")