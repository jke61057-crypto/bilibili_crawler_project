import os
import time
import json
from curl_cffi import requests
session = requests.Session(impersonate="chrome110")
import hashlib
import urllib.parse

# ==========================================
# 请在此处填入您的 B 站 SESSDATA
SESSDATA = "" 
MID = "3706972811561025"
# ==========================================

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Referer': f'https://space.bilibili.com/{MID}/video',
    'Cookie': f'SESSDATA={SESSDATA}'
}

# 强制不走系统代理，防止 VPN 节点屏蔽 B 站导致 Timeout
PROXIES = {
    "http": None,
    "https": None,
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
    resp = session.get('https://api.bilibili.com/x/web-interface/nav', headers=headers, proxies=PROXIES)
    resp.raise_for_status()
    json_content = resp.json()
    img_url = json_content['data']['wbi_img']['img_url']
    sub_url = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key

def get_user_videos_wbi(mid):
    print("正在使用 B 站官方 WBI 签名接口获取视频列表...")
    try:
        img_key, sub_key = getWbiKeys()
    except Exception as e:
        print(f"[-] 获取 WBI Keys 失败 (可能需要更新 Cookie): {e}")
        return []
        
    videos = []
    page = 1
    while True:
        print(f"  -> 正在拉取第 {page} 页视频...")
        params = {
            'mid': mid,
            'pn': page,
            'ps': 30,
            'index': 1,
            'jsonp': 'jsonp'
        }
        signed_params = encWbi(params, img_key, sub_key)
        
        try:
            resp = session.get('https://api.bilibili.com/x/space/wbi/arc/search', params=signed_params, headers=headers, proxies=PROXIES)
            data = resp.json()
            if data['code'] != 0:
                print(f"  [-] 获取视频列表失败: {data['message']}")
                break
                
            vlist = data['data']['list']['vlist']
            if not vlist:
                break
                
            for v in vlist:
                videos.append({
                    'bvid': v['bvid'],
                    'title': v['title']
                })
            page += 1
            time.sleep(2) # 防风控
        except Exception as e:
            print(f"  [-] 请求视频列表异常: {e}")
            break
            
    return videos

def get_video_subtitle_requests(bvid, title):
    safe_print_title = title.encode('gbk', errors='ignore').decode('gbk')
    print(f"正在获取视频信息: {bvid} - {safe_print_title}")
    
    # 1. 获取视频 cid
    try:
        view_res = session.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers, proxies=PROXIES, timeout=10)
        data = view_res.json()
        if data.get('code') != 0:
            print(f"  [-] 获取视频信息失败: {data.get('message')}")
            return None
        cid = data['data']['cid']
    except Exception as e:
        print(f"  [-] 解析视频详情异常: {e}")
        return None
    
    # 2. 获取字幕列表
    try:
        player_res = session.get(f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", headers=headers, proxies=PROXIES, timeout=10)
        data2 = player_res.json()
        if data2.get('code') != 0:
            print(f"  [-] 获取字幕列表失败: {data2.get('message')}")
            return None
            
        subtitles = data2['data'].get('subtitle', {}).get('subtitles', [])
        if not subtitles:
            print(f"  [-] 视频没有可用的字幕")
            return None
            
        sub_url = subtitles[0].get('subtitle_url', '')
        if not sub_url:
            print(f"  [-] 字幕URL为空")
            return None
            
        if sub_url.startswith('//'):
            sub_url = 'https:' + sub_url
    except Exception as e:
        print(f"  [-] 解析字幕列表异常: {e}")
        return None
        
    # 3. 下载字幕
    try:
        sub_res = session.get(sub_url, headers=headers, proxies=PROXIES, timeout=10)
        sub_data = sub_res.json()
        body = sub_data.get('body', [])
        text = "\n".join([item['content'] for item in body])
        return text
    except Exception as e:
        print(f"  [-] 下载或解析字幕内容异常: {e}")
        return None

def main():
    save_dir = "bilibili_subtitles"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    videos = get_user_videos_wbi(MID)
    print(f"\n共找到 {len(videos)} 个视频，开始下载字幕...\n")
    
    for video in videos:
        bvid = video['bvid']
        title = video['title']
        
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ' or c=='_']).rstrip()
        file_path = os.path.join(save_dir, f"{safe_title}_{bvid}.txt")
        
        if os.path.exists(file_path):
            safe_print_title = title.encode('gbk', errors='ignore').decode('gbk')
            print(f"  [+] 已存在，跳过: {safe_print_title}")
            continue
            
        subtitle_text = get_video_subtitle_requests(bvid, title)
        if subtitle_text:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(subtitle_text)
            safe_print_path = file_path.encode('gbk', errors='ignore').decode('gbk')
            print(f"  [+] 成功保存字幕: {safe_print_path}")
            
        time.sleep(2)

if __name__ == "__main__":
    main()
