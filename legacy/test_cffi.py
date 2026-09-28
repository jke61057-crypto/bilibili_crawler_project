from curl_cffi import requests
PROXIES = {"http": None, "https": None}
session = requests.Session(impersonate="chrome110")
try:
    res = session.get("https://api.bilibili.com", proxies=PROXIES)
    print(res.status_code)
except Exception as e:
    print(f"Error: {e}")
