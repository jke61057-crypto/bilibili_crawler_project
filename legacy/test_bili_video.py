import requests
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_subtitle(bvid):
    # 1. Get video info to get cid
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return f"Error: Status code {resp.status_code}"
    
    try:
        data = resp.json()
    except:
        return "Error: Could not parse JSON. Probably blocked."
        
    if data['code'] != 0:
        return f"Error from API: {data['message']}"
        
    cid = data['data']['cid']
    print(f"Got CID: {cid}")
    
    # 2. Get subtitle url
    player_url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
    # need cookies? we'll see
    resp2 = requests.get(player_url, headers=headers)
    try:
        data2 = resp2.json()
    except:
        return "Error: Could not parse player JSON"
        
    if data2['code'] != 0:
        return f"Error from player API: {data2['message']}"
        
    subtitles = data2['data'].get('subtitle', {}).get('subtitles', [])
    if not subtitles:
        return "No subtitles found"
        
    sub_url = subtitles[0]['subtitle_url']
    if sub_url.startswith('//'):
        sub_url = 'https:' + sub_url
        
    print(f"Got subtitle URL: {sub_url}")
    
    # 3. Download subtitle
    resp3 = requests.get(sub_url, headers=headers)
    sub_data = resp3.json()
    
    body = sub_data.get('body', [])
    text = " ".join([item['content'] for item in body])
    return text

if __name__ == "__main__":
    bvid = "BV1LCG36dED2"
    text = get_subtitle(bvid)
    print("SUBTITLES:")
    print(text[:500])
    with open("subtitle.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved to subtitle.txt")
