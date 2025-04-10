import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        print("Launching browser...")
        try:
            # Explicitly launch headless to match Docker setup
            browser = await p.chromium.launch(headless=True) 
            print("Browser launched.")
            page = await browser.new_page()
            print("Page created.")
            print("Navigating to http://example.com...")
            await page.goto("http://example.com", timeout=60000) # 60 second timeout
            print("Navigation successful!")
            print("Closing browser...")
            await browser.close()
            print("Browser closed.")
        except Exception as e:
            print(f"An error occurred: {e}")
            # Attempt cleanup if browser exists
            if 'browser' in locals() and browser.is_connected():
                try:
                    await browser.close()
                    print("Browser closed after error.")
                except Exception as close_e:
                    print(f"Error closing browser after error: {close_e}")

if __name__ == "__main__":
    asyncio.run(main()) 