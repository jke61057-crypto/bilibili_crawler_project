import time
import os
import json
import requests
from playwright.sync_api import sync_playwright

SESSDATA = ""
MID = "3706972811561025"

def get_all_bilibili_videos():
    print("正在启动 Playwright 防检测引擎抓取完整视频列表...")
    videos = []
    seen = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        context.add_cookies([{
            'name': 'SESSDATA',
            'value': SESSDATA,
            'domain': '.bilibili.com',
            'path': '/'
        }])
        page = context.new_page()
        
        # 注入防检测脚本
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {} };
        """)
        
        page_num = 1
        while True:
            url = f"https://space.bilibili.com/{MID}/upload/video?tid=0&page={page_num}&keyword=&order=pubdate"
            print(f"正在读取第 {page_num} 页: {url}")
            page.goto(url)
            page.wait_for_timeout(3000)
            
            # 找到所有卡片
            cards = page.locator(".bili-video-card, .small-item").all()
            if not cards:
                print(f"第 {page_num} 页未查找到卡片，尝试重试...")
                page.wait_for_timeout(3000)
                cards = page.locator(".bili-video-card, .small-item").all()
                if not cards:
                    print("已无更多卡片，抓取结束。")
                    break
                    
            page_found = 0
            for card in cards:
                try:
                    # 获取 title 属性
                    title_el = card.locator(".bili-video-card__info--tit, a.title, [title]").first
                    title = title_el.get_attribute("title") or title_el.inner_text()
                    title = title.strip()
                    
                    link_el = card.locator("a[href*='/video/BV']").first
                    href = link_el.get_attribute("href")
                    
                    if href and "/video/BV" in href and title:
                        bvid = href.split("/video/")[1].split("/")[0].split("?")[0]
                        if bvid not in seen:
                            seen.add(bvid)
                            videos.append({'title': title, 'bvid': bvid})
                            page_found += 1
                except Exception as e:
                    continue
            
            print(f"  -> 第 {page_num} 页抓取到 {page_found} 个视频，累计 {len(videos)} 个。")
            
            # 尝试点击下一页按钮
            next_btn = page.locator(".be-pager-next:not(.be-pager-disabled), .vui_pagenation--btn-side:last-child").first
            if next_btn.is_visible() and not next_btn.is_disabled():
                page_num += 1
            else:
                break
                
        browser.close()
    return videos

if __name__ == "__main__":
    v = get_all_bilibili_videos()
    print(f"共获取到 {len(v)} 个真实视频。")
    with open("all_videos.json", "w", encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=2)
