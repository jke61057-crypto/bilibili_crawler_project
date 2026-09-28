import time
import json
import requests
import hashlib
import urllib.parse
from curl_cffi import requests as cffi_requests

SESSDATA = ""

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/video/BV1qq6ZYNEwv/',
    'Cookie': f'SESSDATA={SESSDATA}'
}

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    return ''.join([orig[i] for i in mixinKeyEncTab])[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time
    params = dict(sorted(params.items()))
    query = urllib.parse.urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = wbi_sign
    return params

session = cffi_requests.Session(impersonate="chrome110")

# 1. Nav to get WBI keys
resp = session.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
json_content = resp.json()
img_url = json_content['data']['wbi_img']['img_url']
sub_url = json_content['data']['wbi_img']['sub_url']
img_key = img_url.rsplit('/', 1)[1].split('.')[0]
sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]

# 2. Call WBI player/v2
params = {
    'bvid': 'BV1qq6ZYNEwv',
    'cid': '27651801357'
}
signed_params = encWbi(params, img_key, sub_key)

wbi_player_url = "https://api.bilibili.com/x/player/wbi/v2"
wbi_res = session.get(wbi_player_url, params=signed_params, headers=headers).json()
print("WBI Player v2 subtitles:")
print(json.dumps(wbi_res.get('data', {}).get('subtitle'), ensure_ascii=False))
