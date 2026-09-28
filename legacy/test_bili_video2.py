import requests
import json
import os

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://www.bilibili.com'
}

def get_subtitle(bvid):
    # 1. Get video info to get cid
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return f"Error: Status code {resp.status_code}"
    
    data = resp.json()
    if data['code'] != 0:
        return f"Error from view API: code {data['code']}, message: {data['message']}"
        
    cid = data['data']['cid']
    title = data['data']['title']
    print(f"Title: {title}, CID: {cid}")
    
    # 2. Get subtitle url
    player_url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
    resp2 = requests.get(player_url, headers=headers)
    data2 = resp2.json()
        
    if data2['code'] != 0:
        return f"Error from player API: code {data2['code']}, message: {data2['message']}"
        
    subtitles = data2['data'].get('subtitle', {}).get('subtitles', [])
    if not subtitles:
        return f"No subtitles found for {bvid}"
        
    sub_url = subtitles[0]['subtitle_url']
    if sub_url.startswith('//'):
        sub_url = 'https:' + sub_url
        
    # 3. Download subtitle
    resp3 = requests.get(sub_url, headers=headers)
    sub_data = resp3.json()
    
    body = sub_data.get('body', [])
    text = " ".join([item['content'] for item in body])
    return text

if __name__ == "__main__":
    bvid = "BV1RZuH6LExF"
    print(f"Fetching subtitle for {bvid}...")
    text = get_subtitle(bvid)
    print("SUBTITLES:")
    print(text[:200])
