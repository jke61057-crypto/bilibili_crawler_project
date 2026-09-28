from playwright.sync_api import sync_playwright
import json

def fetch_json(page, url):
    js_code = f"""
    async () => {{
        let res = await fetch("{url}");
        return await res.text();
    }}
    """
    return json.loads(page.evaluate(js_code))

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://search.bilibili.com/")
        page.wait_for_timeout(2000)
        
        url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=土豆看财报&page=1"
        data = fetch_json(page, url)
        
        results = data['data']['result']
        for item in results[:3]:
            print(item.get('mid'), item.get('author'))
            
        browser.close()

if __name__ == "__main__":
    main()
