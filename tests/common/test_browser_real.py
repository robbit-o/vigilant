"""Real-browser checks for the block debounce.

Mocks cannot reproduce the `wait_for_function` immediate-evaluation behavior
that gutted the original debounce, so these drive a real headless Chromium
against a local page whose body toggles the block wording in real time.
"""

import time

import pytest
from playwright.sync_api import Error as PlaywrightError, TimeoutError, sync_playwright

from vigilant.common.browser import OUTCOME_BLOCKED, wait_for_outcome

SUCCESS_URL: str = "https://portal.example.com/home"
BLOCKED_TEXT: str = "inténtelo más tarde"


@pytest.fixture()
def chromium_page():
    """A real headless Chromium page, skipped when the browser is absent."""
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(args=["--no-sandbox"])
    except PlaywrightError as error:
        if "Executable doesn't exist" in str(error):
            pytest.skip(f"Playwright browser not installed: {error}")
        raise

    page = browser.new_page()
    page.set_content("<html><body></body></html>")
    yield page
    browser.close()
    playwright.stop()


def test_block_debounce_persists_in_real_time(chromium_page) -> None:
    chromium_page.evaluate("document.body.innerText = 'inténtelo más tarde'")

    started: float = time.monotonic()
    outcome: str = wait_for_outcome(
        chromium_page,
        SUCCESS_URL,
        blocked_texts=[BLOCKED_TEXT],
        blocked_persistence_ms=800.0,
        timeout=4000.0,
    )
    elapsed: float = time.monotonic() - started

    # the block is only reported after the window elapses in real time; the
    # pre-fix code resolved it in milliseconds
    assert outcome == OUTCOME_BLOCKED
    assert elapsed >= 0.7
    assert elapsed < 4.0


def test_block_debounce_ignores_transient_blip(chromium_page) -> None:
    chromium_page.evaluate(
        "(function() {"
        "  document.body.innerText = 'inténtelo más tarde';"
        "  setTimeout(function() { document.body.innerText = ''; }, 700);"
        "})()"
    )

    started: float = time.monotonic()
    with pytest.raises(TimeoutError):
        wait_for_outcome(
            chromium_page,
            SUCCESS_URL,
            blocked_texts=[BLOCKED_TEXT],
            blocked_persistence_ms=3000.0,
            timeout=2500.0,
        )
    elapsed: float = time.monotonic() - started

    # the momentary notice never became a block report; the watch ran on to
    # the overall deadline instead
    assert elapsed >= 2.0
