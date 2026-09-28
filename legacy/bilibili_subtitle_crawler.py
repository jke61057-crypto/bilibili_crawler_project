import requests
import json
import os
import time

# ==========================================
# 请在此处填入您的 B 站 SESSDATA Cookie
# 获取方法：在浏览器登录 B 站 -> F12 打开开发者工具 -> Application (应用) -> Cookies -> 找到 SESSDATA 的值
SESSDATA = ""
# ==========================================

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://space.bilibili.com/',
    'Cookie': f'SESSDATA={SESSDATA}'
}

def search_user_videos(keyword, pages=1):
    """通过搜索接口获取UP主的视频（绕过WBI签名限制的简易方法）"""
    print(f"正在搜索UP主：{keyword}")
    videos = []
    
    search_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://search.bilibili.com/'
    }
    
    for page in range(1, pages + 1):
        url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={keyword}&page={page}"
        try:
            resp = requests.get(url, headers=search_headers)
            data = resp.json()
            if data['code'] == 0:
                results = data['data'].get('result', [])
                for item in results:
                    videos.append({
                        'bvid': item['bvid'],
                        'title': item['title'].replace('<em class="keyword">', '').replace('</em>', '')
                    })
            else:
                print(f"搜索失败: {data['message']}")
                break
        except Exception as e:
            print(f"搜索异常: {e}")
        time.sleep(1) # 避免请求过快
    return videos

def get_video_subtitle(bvid, title):
    """获取指定视频的字幕"""
    safe_print_title = title.encode('gbk', errors='ignore').decode('gbk')
    print(f"正在获取视频信息: {bvid} - {safe_print_title}")
    # 1. 获取视频 cid
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"  [-] 请求失败: 状态码 {resp.status_code}")
        return None
    
    data = resp.json()
    if data['code'] != 0:
        print(f"  [-] 获取视频信息失败: {data['message']} (可能需要有效的SESSDATA)")
        return None
        
    cid = data['data']['cid']
    
    # 2. 获取字幕列表
    player_url = f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}"
    resp2 = requests.get(player_url, headers=headers)
    data2 = resp2.json()
        
    if data2['code'] != 0:
        print(f"  [-] 获取字幕列表失败: {data2['message']}")
        return None
        
    subtitles = data2['data'].get('subtitle', {}).get('subtitles', [])
    if not subtitles:
        print(f"  [-] 视频没有可用的字幕 (可能未生成AI字幕或UP主未上传)")
        return None
        
    # 取第一个字幕（通常是中文AI字幕）
    sub_url = subtitles[0].get('subtitle_url', '')
    if not sub_url:
        print(f"  [-] 字幕URL为空")
        return None
        
    if sub_url.startswith('//'):
        sub_url = 'https:' + sub_url
        
    # 3. 下载并解析字幕
    resp3 = requests.get(sub_url, headers=headers)
    sub_data = resp3.json()
    
    body = sub_data.get('body', [])
    text = "\n".join([item['content'] for item in body])
    return text

def main():
    if SESSDATA == "请替换为您的SESSDATA":
        print("警告：您尚未填入 SESSDATA，某些需要登录的API（如获取AI字幕）可能会失败！")
    
    up_name = "土豆看财报"
    save_dir = "bilibili_subtitles"
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    # 获取视频列表（默认获取第一页）
    videos = search_user_videos(up_name, pages=1)
    print(f"共找到 {len(videos)} 个视频")
    
    for video in videos:
        bvid = video['bvid']
        title = video['title']
        
        # 处理Windows文件名中的非法字符
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ' or c=='_']).rstrip()
        file_path = os.path.join(save_dir, f"{safe_title}_{bvid}.txt")
        
        if os.path.exists(file_path):
            safe_print_title = title.encode('gbk', errors='ignore').decode('gbk')
            print(f"  [+] 已存在，跳过: {safe_print_title}")
            continue
            
        subtitle_text = get_video_subtitle(bvid, title)
        if subtitle_text:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(subtitle_text)
            safe_print_path = file_path.encode('gbk', errors='ignore').decode('gbk')
            print(f"  [+] 成功保存字幕: {safe_print_path}")
            
        time.sleep(2) # 避免触发风控

if __name__ == "__main__":
    main()
