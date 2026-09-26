from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import Optional

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Video,
    sync_playwright,
)

from vigilant import logger
from vigilant.common import options
from vigilant.common.exceptions import DriverException
from vigilant.common.scripts import MOUSE_POINTER_SCRIPT
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

    with ExitStack() as stack:
        p = stack.enter_context(sync_playwright())
        videos_path: str = (
            stack.enter_context(TemporaryDirectory())
            if browser_options.record_video
            else ""
        )

        browser: Browser = p.chromium.launch(
            channel="chrome",
            headless=browser_options.headless,
            args=browser_args,
        )
        context: BrowserContext = browser.new_context(
            **_context_options(browser_options, videos_path)
        )
        page: Page = context.new_page()
        page.set_default_timeout(settings.BROWSER_WAIT_TIMEOUT)

        if browser_options.record_video:
            page.add_init_script(MOUSE_POINTER_SCRIPT)

        video: Optional[Video] = page.video if browser_options.record_video else None

        try:
            yield page
        except Exception as e:
            logger.exception(e)
            screenshot_path: str = _take_screenshot(page)

            raise DriverException(screenshot_path)
        finally:
            context.close()

            if video:
                _save_video(video)

            browser.close()


def _context_options(
    browser_options: options.BrowserOptions, videos_path: str
) -> dict[str, object]:
    """Builds the browser context options for the current configuration

    Args:
        browser_options (options.BrowserOptions): Browser options
        videos_path (str): Directory where the video is recorded, empty
            disables the recording

    Returns:
        dict[str, object]: Browser context options
    """
    context_options: dict[str, object] = {
        "accept_downloads": True,
        "viewport": browser_options.viewport,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36",
    }

    if browser_options.record_video:
        context_options["record_video_dir"] = videos_path
        context_options["record_video_size"] = browser_options.viewport

    return context_options


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


def _save_video(video: Video) -> str:
    """Saves the recorded browser session in storage.

    Args:
        video (Video): Recorded video object
    """
    date_now: str = datetime.now().strftime("%Y%m%d%H%M%S")
    video_path: str = f"{IOResources.SCREENSHOTS_PATH}/browser-{date_now}.webm"

    saved_path: str = storage.save_video(str(video.path()), video_path)

    logger.info(f"\N{VIDEO CAMERA} Browser video saved at: {saved_path}")
    return saved_path
