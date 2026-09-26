from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    sync_playwright,
)

from vigilant import logger
from vigilant.common import options
from vigilant.common.exceptions import DriverException
from vigilant.common.storage import GoogleCloudStorage, LocalStorage
from vigilant.common.values import (
    settings,
    IOResources,
    StorageLocation,
)

storage = (
    GoogleCloudStorage()
    if settings.STORAGE_LOCATION == StorageLocation.GCS
    else LocalStorage()
)


@contextmanager
def session() -> Generator[Page]:
    with sync_playwright() as p:
        browser_options: options.BrowserOptions = options.current
        browser_args: list[str] = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]

        if not browser_options.headless:
            browser_args.append(
                f"--window-size={browser_options.width},{browser_options.height}"
            )

        browser: Browser = p.chromium.launch(
            channel="chrome",
            headless=browser_options.headless,
            args=browser_args,
        )
        context: BrowserContext = browser.new_context(
            accept_downloads=True,
            viewport=browser_options.viewport,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36",
        )
        page: Page = context.new_page()
        page.set_default_timeout(settings.BROWSER_WAIT_TIMEOUT)

        try:
            yield page
        except Exception as e:
            logger.exception(e)
            screenshot_path: str = _take_screenshot(page)

            raise DriverException(screenshot_path)
        finally:
            browser.close()


def _take_screenshot(page: Page) -> str:
    """Takes a screenshot of the browser window and saves it in storage.

    Args:
        driver (Page): Chrome page object
    """
    date_now: str = datetime.now().strftime("%Y%m%d%H%M%S")
    screenshot_path: str = f"{IOResources.SCREENSHOTS_PATH}/browser-{date_now}.png"

    image_data: bytes = page.screenshot(full_page=True)
    saved_path: str = storage.save_image(image_data, screenshot_path)

    logger.info(f"\N{CAMERA} Browser screenshot saved at: {saved_path}")
    return saved_path
