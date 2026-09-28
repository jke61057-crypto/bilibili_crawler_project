from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://space.bilibili.com/3706972811561025/video")
        page.wait_for_timeout(5000)
        
        # 尝试从DOM获取
        cards = page.locator(".bili-video-card").all()
        print(f"Found {len(cards)} cards")
        for card in cards[:5]:
            title_el = card.locator(".bili-video-card__info--tit")
            if title_el.count() > 0:
                title = title_el.get_attribute("title")
                href = title_el.get_attribute("href")
                print(f"Title: {title.encode('gbk', 'ignore').decode('gbk')}, Href: {href}")
                
        browser.close()

if __name__ == "__main__":
    main()
