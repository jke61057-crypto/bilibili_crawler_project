import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=土豆看财报"
resp = requests.get(url, headers=headers)
print(resp.status_code)
try:
    data = resp.json()
    if data['code'] == 0:
        for item in data['data']['result'][:5]:
            print(f"{item['bvid']} - {item['title']}")
    else:
        print(data)
except Exception as e:
    print(e)
