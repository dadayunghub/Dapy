from playwright.sync_api import sync_playwright

URL = "https://google.com"
OUTPUT = "screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL, timeout=60000)
    page.wait_for_load_state("networkidle")

    page.screenshot(path=OUTPUT, full_page=True)
    print(f"Screenshot saved as {OUTPUT}")

    browser.close()
