import requests
import xml.etree.ElementTree as ET
import re

def get_bvid_from_rss(uid):
    url = f"https://rsshub.app/bilibili/user/video/{uid}"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        root = ET.fromstring(res.content)
        videos = []
        for item in root.findall('.//item'):
            title = item.find('title').text
            link = item.find('link').text
            # link is usually https://www.bilibili.com/video/BV1...
            match = re.search(r'video/(BV[a-zA-Z0-9]+)', link)
            if match:
                bvid = match.group(1)
                videos.append({'title': title, 'bvid': bvid})
        return videos
    except Exception as e:
        print(f"RSS fetch failed: {e}")
        return []

v = get_bvid_from_rss('3706972811561025')
print(f"Found {len(v)} videos via RSS")
for x in v[:5]:
    print(x)
