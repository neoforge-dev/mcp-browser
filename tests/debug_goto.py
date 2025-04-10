import asyncio
from playwright.async_api import async_playwright
import time
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("debug-goto")

async def main():
    async with async_playwright() as p:
        browser = None
        try:
            logger.info("Launching Chromium with --no-sandbox...")
            browser = await p.chromium.launch(args=["--no-sandbox"])
            page = await browser.new_page()
            
            data_url = "data:text/html,<html><body>Debug Hello</body></html>"
            logger.info(f"Attempting page.goto('{data_url}') with 30s timeout...")
            
            start_time = time.monotonic()
            try:
                await asyncio.wait_for(
                    page.goto(data_url, wait_until="domcontentloaded"),
                    timeout=30.0
                )
                end_time = time.monotonic()
                logger.info(f"page.goto succeeded in {end_time - start_time:.2f} seconds.")
                content = await page.content()
                logger.info(f"Page content: {content[:100]}...") # Log first 100 chars
                
            except asyncio.TimeoutError:
                end_time = time.monotonic()
                logger.error(f"page.goto timed out after {end_time - start_time:.2f} seconds.")
            except Exception as e:
                end_time = time.monotonic()
                logger.error(f"page.goto failed after {end_time - start_time:.2f} seconds with error: {type(e).__name__} - {e}", exc_info=True)
                
            await page.close()
            
        except Exception as e:
            logger.error(f"An error occurred during setup or execution: {e}", exc_info=True)
        finally:
            if browser:
                logger.info("Closing browser...")
                await browser.close()
                logger.info("Browser closed.")

if __name__ == "__main__":
    asyncio.run(main()) 