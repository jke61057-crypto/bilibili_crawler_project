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
        page.screenshot(path="screenshot.png")
        print("Screenshot saved to screenshot.png")
        browser.close()

if __name__ == "__main__":
    main()
