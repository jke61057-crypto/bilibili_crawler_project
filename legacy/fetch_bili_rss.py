import requests
import xml.etree.ElementTree as ET
import re

url = "https://rsshub.app/bilibili/user/video/3706972811561025"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

try:
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    items = root.findall('.//item')
    print(f"Found {len(items)} videos")
    for item in items[:5]:
        link = item.find('link').text
        bvid_match = re.search(r'BV\w+', link)
        if bvid_match:
            print(f"BVID: {bvid_match.group(0)}, Title: {item.find('title').text}")
except Exception as e:
    print(f"Error: {e}")
