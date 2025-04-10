import asyncio
from playwright.async_api import async_playwright

async def main():
    print("Starting host Playwright test...")
    async with async_playwright() as p:
        print("Launching Chromium (headless)...")
        try:
            browser = await p.chromium.launch(headless=True)
            print("Chromium launched successfully.")
            
            print("Creating new page...")
            page = await browser.new_page()
            print("Page created.")
            
            print("Navigating to http://example.com...")
            await page.goto("http://example.com")
            print("Successfully navigated to http://example.com")
            
            print("Closing browser...")
            await browser.close()
            print("Browser closed.")
            print("\nHost Playwright test successful!")
            
        except Exception as e:
            print(f"\nAn error occurred during the host Playwright test: {e}")
            # Ensure browser is closed even if error occurs before explicit close
            if 'browser' in locals() and not browser.is_closed():
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 