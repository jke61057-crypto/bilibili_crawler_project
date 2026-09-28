import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://space.bilibili.com/3706972811561025'
}

# Try getting user info
uid = "3706972811561025"
url = f"https://api.bilibili.com/x/space/wbi/arc/search?mid={uid}&pn=1&ps=30"
try:
    res = requests.get(url, headers=headers)
    print(res.status_code)
    print(res.text[:500])
except Exception as e:
    print(e)
