import hashlib
import time
import urllib.parse
import requests

SESSDATA = ""

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://space.bilibili.com/3706972811561025',
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

def getWbiKeys():
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
    resp.raise_for_status()
    json_content = resp.json()
    img_url = json_content['data']['wbi_img']['img_url']
    sub_url = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

def get_videos(mid):
    try:
        img_key, sub_key = getWbiKeys()
    except Exception as e:
        print(f"Failed to get WBI keys: {e}")
        return
        
    params = {
        'mid': mid,
        'pn': 1,
        'ps': 30,
        'index': 1,
        'jsonp': 'jsonp'
    }
    signed_params = encWbi(params, img_key, sub_key)
    
    resp = requests.get('https://api.bilibili.com/x/space/wbi/arc/search', params=signed_params, headers=headers)
    try:
        data = resp.json()
        print(data['code'])
        if data['code'] == 0:
            print(f"Found {len(data['data']['list']['vlist'])} videos")
            for item in data['data']['list']['vlist'][:5]:
                print(item['bvid'], item['title'].encode('gbk', 'ignore').decode('gbk'))
        else:
            print(f"Error: {data['message']}")
    except Exception as e:
        print(f"Error parsing response: {e}")

if __name__ == "__main__":
    get_videos('3706972811561025')
