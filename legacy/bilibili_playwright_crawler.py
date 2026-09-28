import os
import time
import json
import requests
from playwright.sync_api import sync_playwright

# ==========================================
# 请在此处填入您的 B 站 SESSDATA
SESSDATA = "" 
MID = "3706972811561025"
# ==========================================

def get_user_videos_from_space(page, mid, max_pages=5):
    print(f"正在通过 UP 主空间提取视频列表 (准备翻 {max_pages} 页)...")
    videos = []
    seen = set()
    
    for p in range(1, max_pages + 1):
        url = f"https://space.bilibili.com/{mid}/video?tid=0&page={p}&keyword=&order=pubdate"
        print(f"  -> 正在加载第 {p} 页...")
        page.goto(url)
        # 等待视频卡片渲染，如果被拦截会有登录框，但底层依然能加载
        try:
            page.wait_for_selector(".bili-video-card__info--tit", timeout=10000)
        except:
            print("  [!] 等待视频卡片超时，可能页面为空或需要手动处理验证码。")
            
        time.sleep(2) # 缓冲一下
        
        cards = page.locator(".bili-video-card__info--tit").all()
        if len(cards) == 0:
            print("  [!] 本页未提取到任何视频，结束翻页。")
            break
            
        for card in cards:
            title = card.get_attribute("title")
            href = card.get_attribute("href")
            if href and "/video/" in href:
                bvid = href.split("/video/")[1].split("/")[0]
                if bvid not in seen:
                    seen.add(bvid)
                    videos.append({
                        'bvid': bvid,
                        'title': title
                    })
        print(f"  -> 第 {p} 页提取完毕，累计找到 {len(videos)} 个视频。")
        time.sleep(2)
        
    return videos

def get_video_subtitle_requests(bvid, title):
    safe_print_title = title.encode('gbk', errors='ignore').decode('gbk')
    print(f"正在获取视频信息: {bvid} - {safe_print_title}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Cookie': f'SESSDATA={SESSDATA}'
    }
    
    # 1. 获取视频 cid
    try:
        view_res = requests.get(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", headers=headers, timeout=10)
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
        player_res = requests.get(f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", headers=headers, timeout=10)
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
        sub_res = requests.get(sub_url, headers=headers, timeout=10)
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

    print("启动浏览器引擎...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        
        # 为了顺利打开空间主页，注入基础 Cookie
        context.add_cookies([{
            'name': 'SESSDATA',
            'value': SESSDATA,
            'domain': '.bilibili.com',
            'path': '/'
        }])
        
        page = context.new_page()
        
        # 使用 DOM 解析获取全部视频 BVID
        videos = get_user_videos_from_space(page, MID, max_pages=5)
        print(f"\n太棒了！共找到 {len(videos)} 个视频。浏览器任务结束，正在转入高速下载模式...\n")
        
        browser.close()
        
    # 直接使用 requests 下载字幕
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
            
        time.sleep(1.5)

if __name__ == "__main__":
    main()
