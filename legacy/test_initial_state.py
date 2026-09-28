import requests
import re
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
res = requests.get("https://space.bilibili.com/3706972811561025/video", headers=headers)
html = res.text

match = re.search(r'window\.__INITIAL_STATE__=(.*?);\(function\(\)', html)
if match:
    data = json.loads(match.group(1))
    print(data.keys())
    # find videos
else:
    print("Not found")
