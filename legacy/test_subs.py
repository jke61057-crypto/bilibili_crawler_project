import requests

headers = {
    'User-Agent': 'Mozilla/5.0'
}
res = requests.get("https://api.bilibili.com/x/web-interface/view?bvid=BV1RZuH6LExF", headers=headers).json()
cid = res['data']['cid']
res2 = requests.get(f"https://api.bilibili.com/x/player/v2?bvid=BV1RZuH6LExF&cid={cid}", headers=headers).json()
subs = res2['data']['subtitle']['subtitles']
print(f"Subtitles for BV1RZuH6LExF: {len(subs)}")
