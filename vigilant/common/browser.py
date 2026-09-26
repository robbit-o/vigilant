from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from datetime import datetime
import random
import re
from tempfile import TemporaryDirectory
import time
from typing import Final, Optional

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    TimeoutError,
    Video,
    sync_playwright,
)

from vigilant import logger
from vigilant.common import options
from vigilant.common.exceptions import DriverException, FieldValueMismatch
from vigilant.common.scripts import MOUSE_POINTER_SCRIPT
from vigilant.common.storage import GoogleCloudStorage, LocalStorage
from vigilant.common.values import (
    settings,
    IOResources,
    StorageLocation,
)

OUTCOME_SUCCESS: Final[str] = "success"
OUTCOME_ERROR: Final[str] = "error"
OUTCOME_BLOCKED: Final[str] = "blocked"
POLL_INTERVAL: Final[float] = 250.0
BLOCKED_PERSISTENCE_MS: Final[float] = 3000.0

# Resolves as soon as the page reaches the expected URL or shows a rejection or
# a block surface, instead of blocking on any outcome until the timeout
# expires. A "blocked" page is the anti-bot answer that refuses to serve the
# session (URL or wording of a "try later"/challenge screen) and is reported
# as soon as it appears so callers can retry instead of idling through the
# whole timeout.
OUTCOME_SCRIPT: Final[str] = """
([successUrl, errorSelector, errorText, blockedTexts, blockedUrl]) => {
    if (window.location.href.startsWith(successUrl)) return "%(success)s";

    if (blockedUrl && window.location.href.includes(blockedUrl)) return "%(blocked)s";

    if (blockedTexts && blockedTexts.length > 0) {
        const text = document.body ? document.body.innerText.toLowerCase() : "";
        if (blockedTexts.some((fragment) => text.includes(fragment.toLowerCase())))
            return "%(blocked)s";
    }

    if (errorSelector) {
        const node = document.querySelector(errorSelector);
        if (node && node.offsetParent !== null) return "%(error)s";
    }

    if (errorText) {
        const text = document.body ? document.body.innerText.toLowerCase() : "";
        if (text.includes(errorText.toLowerCase())) return "%(error)s";
    }

    return false;
}
""" % {
    "success": OUTCOME_SUCCESS,
    "blocked": OUTCOME_BLOCKED,
    "error": OUTCOME_ERROR,
}

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
            channel=settings.BROWSER_CHANNEL,
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


def wait_for_outcome(
    page: Page,
    success_url: str,
    error_selector: str = "",
    error_text: str = "",
    blocked_texts: Optional[list[str]] = None,
    blocked_url: Optional[str] = None,
    timeout: Optional[float] = None,
    blocked_persistence_ms: float = BLOCKED_PERSISTENCE_MS,
) -> str:
    """Waits until the page reaches a destination, reports a rejection, or
    reports a block.

    Watching the three conditions at once means a form that refuses the
    attempt is reported straight away, rather than after the full timeout
    expires, and a page that refuses to serve the session (anti-bot screen) is
    told apart from a credentials rejection.

    A block is only reported once it stays on screen for `blocked_persistence_ms`
    of real time, so a momentary "try later" notice neither kills the run nor
    races the error screenshot ahead of the block screen render. A success or
    rejection that surfaces during that window wins instead.

    Args:
        page (Page): Chrome page object
        success_url (str): URL the page is expected to reach once done
        error_selector (str): Selector of a visible node that reports the
            rejection, empty to ignore it
        error_text (str): Wording that reports the rejection, empty to ignore it
        blocked_texts (Optional[list[str]]): Wordings of a page that refuses to
            serve the session, empty to ignore them
        blocked_url (Optional[str]): URL substring of a block or challenge
            page, empty to ignore it
        timeout (Optional[float]): Time to wait for either condition, defaults
            to the configured browser timeout
        blocked_persistence_ms (float): How long a block must stay on screen
            in real time before it is reported

    Returns:
        str: `OUTCOME_SUCCESS` when the destination is reached, `OUTCOME_ERROR`
            when the portal reports a rejection and `OUTCOME_BLOCKED` when an
            anti-bot or "try later" screen is served and persists

    Raises:
        TimeoutError: When no condition is met before the timeout
    """
    deadline: float = time.monotonic() + (
        (settings.BROWSER_WAIT_TIMEOUT if timeout is None else timeout) / 1000.0
    )
    payload: list[object] = [
        success_url,
        error_selector,
        error_text,
        blocked_texts or [],
        blocked_url,
    ]

    while True:
        # Primary watch: the destination, a rejection or a block shows first
        outcome = _poll_outcome(page, payload, _remaining(deadline))
        if outcome is None:
            raise TimeoutError("wait_for_outcome: no outcome before the timeout")

        if outcome != OUTCOME_BLOCKED:
            return outcome

        if blocked_persistence_ms <= 0:
            return OUTCOME_BLOCKED

        # A "blocked" page was seen once. Sustain the watch across a real
        # wall-clock window before reporting it, so a momentary "try later"
        # notice neither kills the run nor races the error screenshot ahead of
        # the block screen render. A success or rejection surfacing meanwhile
        # wins, and a block that clears sends the watch back to the primary
        # outcome. The window is paced by `wait_for_timeout`: polling alone
        # would resolve instantly on an already-blocked page and never span
        # the requested time.
        window_end: float = min(
            time.monotonic() + blocked_persistence_ms / 1000.0,
            deadline,
        )
        first_seen: float = time.monotonic()
        while time.monotonic() < window_end:
            page.wait_for_timeout(
                min(POLL_INTERVAL, (window_end - time.monotonic()) * 1000.0)
            )
            state = _poll_outcome(page, payload, timeout_ms=POLL_INTERVAL)
            if state is None:
                break
            if state != OUTCOME_BLOCKED:
                return state
        else:
            logger.info(
                f"Anti-bot screen confirmed after {time.monotonic() - first_seen:.1f}s"
            )
            return OUTCOME_BLOCKED


def _remaining(deadline: float) -> float:
    """Milliseconds left before the deadline, never below zero"""
    return max(0.0, (deadline - time.monotonic()) * 1000.0)


def _poll_outcome(
    page: Page, payload: list[object], timeout_ms: float
) -> Optional[str]:
    """Runs the outcome script once and returns the page state.

    Args:
        page (Page): Chrome page object
        payload (list[object]): Arguments the outcome script reads
        timeout_ms (float): Milliseconds to wait for a condition

    Returns:
        Optional[str]: `OUTCOME_SUCCESS`, `OUTCOME_ERROR`, `OUTCOME_BLOCKED`
            or `None` when no condition shows before the timeout
    """
    if timeout_ms <= 0:
        return None

    try:
        return page.wait_for_function(
            OUTCOME_SCRIPT,
            arg=payload,
            timeout=timeout_ms,
            polling=POLL_INTERVAL,
        ).json_value()
    except TimeoutError:
        return None


def fill_like_human(
    page: Page, selector: str, text: str, numeric_only: bool = False
) -> None:
    """Types text into a field at a human pace and checks that it landed.

    `Locator.fill` writes the whole value in one synthetic input event, with no
    keystrokes and no delay, which is what login forms read as automation.
    Typing key by key also lets the page apply its own input handlers, such as
    RUT formatting. The check afterwards keeps a mistyped or reformatted field
    from being submitted.

    Args:
        page (Page): Chrome page object
        selector (str): Field selector
        text (str): Text to type
        numeric_only (bool): Compare only the digits, for fields that reformat
            the typed text

    Raises:
        FieldValueMismatch: When the field does not end up holding `text`
    """
    field: Locator = page.locator(selector)

    _hover_and_click(page, field)
    page.wait_for_timeout(random.uniform(150, 350))
    field.press_sequentially(text, delay=random.uniform(70, 150))
    page.wait_for_timeout(random.uniform(120, 260))

    _assert_field_value(page, selector, text, numeric_only)


def click_like_human(page: Page, selector: str, hold: Optional[float] = None) -> None:
    """Clicks an element after an irregular mouse trail.

    `Locator.click` teleports the pointer, so the page only ever observes a
    single mousemove before the click. A trail plus a hover pause is what a real
    approach looks like to the event listeners the page collects.

    Args:
        page (Page): Chrome page object
        selector (str): Element selector
        hold (Optional[float]): Milliseconds the pointer stays pressed, defaults
            to a short random press
    """
    _hover_and_click(page, page.locator(selector), hold)


def _assert_field_value(
    page: Page, selector: str, text: str, numeric_only: bool
) -> None:
    """Checks that a field holds the value that was typed into it.

    Args:
        page (Page): Chrome page object
        selector (str): Field selector
        text (str): Text that was typed
        numeric_only (bool): Compare only the digits

    Raises:
        FieldValueMismatch: When the field does not hold the expected value
    """
    landed: str = page.locator(selector).input_value()

    if numeric_only:
        matches = _digits(landed) == _digits(text)
    else:
        matches = landed == text

    if not matches:
        raise FieldValueMismatch(selector)


def _digits(text: str) -> str:
    """Strips every character that is not a digit.

    Args:
        text (str): Text to strip

    Returns:
        str: The digits the text is made of
    """
    return re.sub(r"\D", "", text)


def _hover_and_click(page: Page, target: Locator, hold: Optional[float] = None) -> None:
    """Moves the pointer to the target through a short trail and clicks it.

    Args:
        page (Page): Chrome page object
        target (Locator): Element to click
        hold (Optional[float]): Milliseconds the pointer stays pressed, defaults
            to a short random press
    """
    box: Optional[dict[str, float]] = target.bounding_box()

    if not box:
        target.click()
        return

    x: float = box["x"] + box["width"] / 2
    y: float = box["y"] + box["height"] / 2
    viewport: dict[str, int] = page.viewport_size or {
        "width": int(x),
        "height": int(y),
    }

    page.mouse.move(
        _clamp(x - random.uniform(60, 280), viewport["width"]),
        _clamp(y - random.uniform(40, 180), viewport["height"]),
    )
    page.wait_for_timeout(random.uniform(80, 200))
    page.mouse.move(x, y, steps=random.randint(8, 16))
    page.wait_for_timeout(random.uniform(120, 300))

    page.mouse.down()
    page.wait_for_timeout(random.uniform(60, 110) if hold is None else hold)
    page.mouse.up()


def _clamp(value: float, limit: int) -> float:
    """Keeps a coordinate inside the viewport.

    Args:
        value (float): Coordinate value
        limit (int): Viewport size along the same axis

    Returns:
        float: Bounded coordinate
    """
    return min(max(value, 0.0), max(limit - 1, 0.0))


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
        "locale": settings.BROWSER_LOCALE,
        "timezone_id": settings.BROWSER_TIMEZONE,
        # Spoofed on purpose: the WAF in front of the target portal answers 403
        # for the honest HeadlessChrome/Linux agent, so this is what keeps the
        # session reachable. The evidence is documented by each scraper.
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
