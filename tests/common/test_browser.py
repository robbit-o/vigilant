from pathlib import Path
from unittest import mock

import pytest

from vigilant.common import browser, options
from vigilant.common.exceptions import DriverException
from vigilant.common.values import settings


@pytest.fixture(autouse=True)
def reset_options() -> None:
    options.configure(options.BrowserOptions())


@pytest.fixture
def mock_playwright() -> mock.MagicMock:
    mock_browser = mock.MagicMock()
    mock_playwright_session = mock.MagicMock()
    mock_playwright_session.chromium.launch.return_value = mock_browser

    with mock.patch("vigilant.common.browser.sync_playwright") as mock_sync_playwright:
        mock_sync_playwright.return_value.__enter__.return_value = (
            mock_playwright_session
        )
        yield mock_playwright_session


def test_session(mock_playwright: mock.MagicMock, mock_page: mock.MagicMock) -> None:
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_context.return_value.new_page.return_value = mock_page

    with browser.session() as session:
        assert session == mock_page

    mock_playwright.chromium.launch.assert_called_once_with(
        channel="chrome",
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    )
    mock_browser.new_context.assert_called_once_with(
        accept_downloads=True,
        viewport={"width": 1920, "height": 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36",
    )
    mock_browser.close.assert_called_once_with()
    mock_page.set_default_timeout.assert_called_once_with(settings.BROWSER_WAIT_TIMEOUT)


def test_session_show_window(
    mock_playwright: mock.MagicMock, mock_page: mock.MagicMock
) -> None:
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_context.return_value.new_page.return_value = mock_page

    options.configure(options.build_browser_options(show_window=True))

    with browser.session() as session:
        assert session == mock_page

    mock_playwright.chromium.launch.assert_called_once_with(
        channel="chrome",
        headless=False,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1536,864",
        ],
    )
    mock_browser.new_context.assert_called_once_with(
        accept_downloads=True,
        viewport={"width": 1536, "height": 864},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36",
    )


def test_session_custom_size(
    mock_playwright: mock.MagicMock, mock_page: mock.MagicMock
) -> None:
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_context.return_value.new_page.return_value = mock_page

    options.configure(options.build_browser_options(width=1280, height=720))

    with browser.session() as session:
        assert session == mock_page

    launch_kwargs: dict = mock_playwright.chromium.launch.call_args.kwargs

    assert launch_kwargs["headless"] is True
    assert "--window-size=1280,720" not in launch_kwargs["args"]
    assert mock_browser.new_context.call_args.kwargs["viewport"] == {
        "width": 1280,
        "height": 720,
    }


@mock.patch("vigilant.common.browser.sync_playwright")
@mock.patch("vigilant.common.browser._take_screenshot")
def test_session_exception(
    mock_take_screenshot: mock.MagicMock, mock_sync_playwright: mock.MagicMock
) -> None:
    mock_browser, mock_playwright_session = mock.MagicMock(), mock.MagicMock()
    mock_playwright_session.chromium.launch.return_value = mock_browser

    mock_playwright_context_manager = mock.MagicMock()
    mock_playwright_context_manager.__enter__.return_value = mock_playwright_session

    mock_sync_playwright.return_value = mock_playwright_context_manager

    with pytest.raises(DriverException):
        with browser.session() as _:
            raise Exception

    mock_take_screenshot.assert_called_once()
    mock_browser.close.assert_called_once()


def test_take_screenshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_page: mock.MagicMock
):
    screenshot_filename: str = "test_sc.png"
    screenshot_path: Path = tmp_path / screenshot_filename
    image_data: bytes = b"Hesitation is defeat!"

    mock_page.screenshot.return_value = image_data
    monkeypatch.setattr(
        "vigilant.common.storage.LocalStorage.save_image",
        lambda *_: screenshot_path.write_bytes(image_data),
    )

    browser._take_screenshot(mock_page)
    image: bytes = screenshot_path.read_bytes()

    assert screenshot_path.exists() and image == image_data
