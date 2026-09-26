from pathlib import Path
from unittest import mock

import pytest
from playwright.sync_api import TimeoutError

from vigilant.common import browser, options
from vigilant.common.exceptions import DriverException, FieldValueMismatch
from vigilant.common.scripts import MOUSE_POINTER_SCRIPT
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


@pytest.fixture
def mock_video() -> mock.MagicMock:
    video = mock.MagicMock()
    video.path.return_value = "/tmp/videos/recorded.webm"
    return video


def test_session(mock_playwright: mock.MagicMock, mock_page: mock.MagicMock) -> None:
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_context.return_value.new_page.return_value = mock_page

    with browser.session() as session:
        assert session == mock_page

    mock_playwright.chromium.launch.assert_called_once_with(
        channel=settings.BROWSER_CHANNEL,
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
        locale=settings.BROWSER_LOCALE,
        timezone_id=settings.BROWSER_TIMEZONE,
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
        channel=settings.BROWSER_CHANNEL,
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
        locale=settings.BROWSER_LOCALE,
        timezone_id=settings.BROWSER_TIMEZONE,
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


@mock.patch("vigilant.common.browser.storage")
def test_session_record_video(
    mock_storage: mock.MagicMock,
    mock_playwright: mock.MagicMock,
    mock_page: mock.MagicMock,
    mock_video: mock.MagicMock,
) -> None:
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_context.return_value.new_page.return_value = mock_page
    mock_page.video = mock_video

    options.configure(options.build_browser_options(record_video=True))

    with browser.session() as session:
        assert session == mock_page

        context_options: dict = mock_browser.new_context.call_args.kwargs
        record_video_dir: str = context_options["record_video_dir"]
        assert Path(record_video_dir).is_dir()

    assert context_options["record_video_size"] == {"width": 1920, "height": 1080}
    assert not Path(record_video_dir).exists()
    mock_page.add_init_script.assert_called_once_with(MOUSE_POINTER_SCRIPT)
    mock_browser.new_context.return_value.close.assert_called_once()
    mock_video.path.assert_called_once()
    mock_storage.save_video.assert_called_once()
    assert mock_storage.save_video.call_args.args[0] == "/tmp/videos/recorded.webm"
    assert mock_storage.save_video.call_args.args[1].startswith("screenshots/browser-")
    assert mock_storage.save_video.call_args.args[1].endswith(".webm")


@mock.patch("vigilant.common.browser.storage")
def test_session_record_video_exception(
    mock_storage: mock.MagicMock,
    mock_playwright: mock.MagicMock,
    mock_page: mock.MagicMock,
    mock_video: mock.MagicMock,
) -> None:
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_context.return_value.new_page.return_value = mock_page
    mock_page.video = mock_video

    options.configure(options.build_browser_options(record_video=True))

    with mock.patch("vigilant.common.browser._take_screenshot", return_value="sc.png"):
        with pytest.raises(DriverException):
            with browser.session() as _:
                raise Exception

    mock_storage.save_video.assert_called_once()
    assert mock_storage.save_image.call_count == 0
    mock_browser.new_context.return_value.close.assert_called_once()


@mock.patch("vigilant.common.browser.storage")
def test_session_without_record_video(
    mock_storage: mock.MagicMock,
    mock_playwright: mock.MagicMock,
    mock_page: mock.MagicMock,
) -> None:
    mock_browser = mock_playwright.chromium.launch.return_value
    mock_browser.new_context.return_value.new_page.return_value = mock_page
    mock_page.video = None

    with browser.session() as session:
        assert session == mock_page

    assert "record_video_dir" not in mock_browser.new_context.call_args.kwargs
    assert "record_video_size" not in mock_browser.new_context.call_args.kwargs
    mock_page.add_init_script.assert_not_called()
    mock_storage.save_video.assert_not_called()
    mock_browser.new_context.return_value.close.assert_called_once()


@mock.patch("vigilant.common.browser.storage")
def test_save_video(mock_storage: mock.MagicMock, mock_video: mock.MagicMock) -> None:
    saved_path: str = browser._save_video(mock_video)

    assert saved_path.startswith("screenshots/browser-") and saved_path.endswith(
        ".webm"
    )
    assert mock_storage.save_video.call_args.args[0] == "/tmp/videos/recorded.webm"


def test_fill_like_human(mock_page: mock.MagicMock) -> None:
    mock_page.viewport_size = {"width": 1920, "height": 1080}
    mock_page.locator.return_value.bounding_box.return_value = {
        "x": 100.0,
        "y": 200.0,
        "width": 300.0,
        "height": 40.0,
    }
    mock_page.locator.return_value.input_value.return_value = "Hesitation is defeat!"

    browser.fill_like_human(mock_page, "#field", "Hesitation is defeat!")

    mock_page.locator.assert_called_with("#field")
    field: mock.MagicMock = mock_page.locator.return_value
    field.press_sequentially.assert_called_once()
    assert field.press_sequentially.call_args.args[0] == "Hesitation is defeat!"
    assert 0 < field.press_sequentially.call_args.kwargs["delay"] <= 150
    assert field.fill.call_count == 0
    assert mock_page.mouse.move.call_count == 2
    mock_page.mouse.down.assert_called_once()
    mock_page.mouse.up.assert_called_once()


def test_fill_like_human_numeric_only(mock_page: mock.MagicMock) -> None:
    mock_page.viewport_size = {"width": 1920, "height": 1080}
    mock_page.locator.return_value.bounding_box.return_value = {
        "x": 100.0,
        "y": 200.0,
        "width": 300.0,
        "height": 40.0,
    }
    mock_page.locator.return_value.input_value.return_value = "19.081.725-3"

    browser.fill_like_human(mock_page, "#rut", "190817253", numeric_only=True)

    mock_page.locator.return_value.press_sequentially.assert_called_once()


def test_fill_like_human_mismatch(mock_page: mock.MagicMock) -> None:
    mock_page.viewport_size = {"width": 1920, "height": 1080}
    mock_page.locator.return_value.bounding_box.return_value = {
        "x": 100.0,
        "y": 200.0,
        "width": 300.0,
        "height": 40.0,
    }
    mock_page.locator.return_value.input_value.return_value = "19.081.725-9"

    with pytest.raises(FieldValueMismatch) as mismatch:
        browser.fill_like_human(mock_page, "#rut", "190817253", numeric_only=True)

    assert "#rut" in str(mismatch.value)
    assert "190817253" not in str(mismatch.value)


def test_fill_like_human_mismatch_text(mock_page: mock.MagicMock) -> None:
    mock_page.locator.return_value.bounding_box.return_value = None
    mock_page.locator.return_value.input_value.return_value = "truncated"

    with pytest.raises(FieldValueMismatch):
        browser.fill_like_human(mock_page, "#password", "Hesitation is defeat!")


def test_click_like_human(mock_page: mock.MagicMock) -> None:
    mock_page.viewport_size = {"width": 1920, "height": 1080}
    mock_page.locator.return_value.bounding_box.return_value = {
        "x": 100.0,
        "y": 200.0,
        "width": 300.0,
        "height": 40.0,
    }

    browser.click_like_human(mock_page, "#button")

    mock_page.locator.assert_called_once_with("#button")
    assert mock_page.mouse.move.call_count == 2
    assert mock_page.mouse.move.call_args.args == (250.0, 220.0)
    assert 8 <= mock_page.mouse.move.call_args.kwargs["steps"] <= 16
    mock_page.mouse.down.assert_called_once()
    mock_page.mouse.up.assert_called_once()
    assert 60 <= mock_page.wait_for_timeout.call_args.args[0] <= 110
    mock_page.locator.return_value.press_sequentially.assert_not_called()


def test_click_like_human_hold(mock_page: mock.MagicMock) -> None:
    mock_page.viewport_size = {"width": 1920, "height": 1080}
    mock_page.locator.return_value.bounding_box.return_value = {
        "x": 100.0,
        "y": 200.0,
        "width": 300.0,
        "height": 40.0,
    }

    browser.click_like_human(mock_page, "#button", hold=500.0)

    mock_page.wait_for_timeout.assert_called_with(500.0)


def test_click_like_human_without_box(mock_page: mock.MagicMock) -> None:
    mock_page.locator.return_value.bounding_box.return_value = None

    browser.click_like_human(mock_page, "#button")

    mock_page.locator.return_value.click.assert_called_once()
    mock_page.mouse.down.assert_not_called()
    mock_page.mouse.up.assert_not_called()


def test_clamp() -> None:
    assert browser._clamp(-50.0, 1920) == 0.0
    assert browser._clamp(5000.0, 1920) == 1919.0
    assert browser._clamp(10.0, 0) == 0.0


def test_wait_for_outcome(mock_page: mock.MagicMock) -> None:
    mock_page.wait_for_function.return_value.json_value.return_value = "success"

    outcome: str = browser.wait_for_outcome(
        mock_page, "https://portal.example.com/home", error_text="datos incorrectos"
    )

    assert outcome == "success"
    assert mock_page.wait_for_function.call_args.args[0] == browser.OUTCOME_SCRIPT
    assert mock_page.wait_for_function.call_args.kwargs["arg"] == [
        "https://portal.example.com/home",
        "",
        "datos incorrectos",
        [],
        None,
    ]
    assert mock_page.wait_for_function.call_args.kwargs["timeout"] == pytest.approx(
        settings.BROWSER_WAIT_TIMEOUT, abs=100
    )
    assert mock_page.wait_for_function.call_args.kwargs["polling"] == (
        browser.POLL_INTERVAL
    )


def _clocked_page(
    mock_page: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> dict[str, float]:
    """Paces the page in wall time: `wait_for_timeout` advances a fake clock."""
    now: dict[str, float] = {"t": 0.0}
    monkeypatch.setattr(browser.time, "monotonic", lambda: now["t"])

    def fake_wait_for_timeout(ms: float) -> None:
        now["t"] += ms / 1000.0

    mock_page.wait_for_timeout.side_effect = fake_wait_for_timeout
    return now


def test_wait_for_outcome_blocked(
    mock_page: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = _clocked_page(mock_page, monkeypatch)
    mock_page.wait_for_function.return_value.json_value.return_value = (
        browser.OUTCOME_BLOCKED
    )

    outcome: str = browser.wait_for_outcome(
        mock_page,
        "https://portal.example.com/home",
        blocked_texts=["no lo podemos atender", "try later"],
        blocked_url="/blocked",
    )

    assert outcome == browser.OUTCOME_BLOCKED
    assert mock_page.wait_for_function.call_args.kwargs["arg"] == [
        "https://portal.example.com/home",
        "",
        "",
        ["no lo podemos atender", "try later"],
        "/blocked",
    ]
    # one primary read plus one read per poll interval, spaced across the
    # persistence window in real time rather than instantly
    polls = int(browser.BLOCKED_PERSISTENCE_MS / browser.POLL_INTERVAL)
    assert mock_page.wait_for_function.call_count == 1 + polls
    assert mock_page.wait_for_timeout.call_count == polls
    assert now["t"] == pytest.approx(browser.BLOCKED_PERSISTENCE_MS / 1000.0)


def test_wait_for_outcome_blocked_immediate(
    mock_page: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clocked_page(mock_page, monkeypatch)
    mock_page.wait_for_function.return_value.json_value.return_value = (
        browser.OUTCOME_BLOCKED
    )

    outcome: str = browser.wait_for_outcome(
        mock_page,
        "https://portal.example.com/home",
        blocked_texts=["no lo podemos atender"],
        blocked_persistence_ms=0,
    )

    assert outcome == browser.OUTCOME_BLOCKED
    assert mock_page.wait_for_function.call_count == 1
    mock_page.wait_for_timeout.assert_not_called()


def test_wait_for_outcome_blocked_sub_poll_window(
    mock_page: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = _clocked_page(mock_page, monkeypatch)
    mock_page.wait_for_function.return_value.json_value.return_value = (
        browser.OUTCOME_BLOCKED
    )

    outcome: str = browser.wait_for_outcome(
        mock_page,
        "https://portal.example.com/home",
        blocked_texts=["no lo podemos atender"],
        blocked_persistence_ms=100,
    )

    assert outcome == browser.OUTCOME_BLOCKED
    # the sub-window window is waited out in one paced read before reporting
    assert mock_page.wait_for_function.call_count == 2
    assert now["t"] == pytest.approx(0.1)


def test_wait_for_outcome_blocked_blip_resolves(
    mock_page: mock.MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = _clocked_page(mock_page, monkeypatch)
    blocked_handle = mock.MagicMock()
    blocked_handle.json_value.return_value = browser.OUTCOME_BLOCKED
    success_handle = mock.MagicMock()
    success_handle.json_value.return_value = browser.OUTCOME_SUCCESS
    mock_page.wait_for_function.side_effect = [blocked_handle, success_handle]

    outcome: str = browser.wait_for_outcome(
        mock_page,
        "https://portal.example.com/home",
        blocked_texts=["no lo podemos atender"],
    )

    assert outcome == browser.OUTCOME_SUCCESS
    # the blip is re-read once, then the live portal wins instead of a block
    assert now["t"] == pytest.approx(browser.POLL_INTERVAL / 1000.0)


def test_wait_for_outcome_expired_before_poll(
    mock_page: mock.MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, int] = {"count": 0}

    def fake_monotonic() -> float:
        calls["count"] += 1
        return 0.0 if calls["count"] == 1 else 60.0

    monkeypatch.setattr(browser.time, "monotonic", fake_monotonic)

    with pytest.raises(TimeoutError):
        browser.wait_for_outcome(
            mock_page, "https://portal.example.com/home", timeout=1000.0
        )

    mock_page.wait_for_function.assert_not_called()
    blocked_handle = mock.MagicMock()
    blocked_handle.json_value.return_value = browser.OUTCOME_BLOCKED
    success_handle = mock.MagicMock()
    success_handle.json_value.return_value = browser.OUTCOME_SUCCESS
    mock_page.wait_for_function.side_effect = [blocked_handle, success_handle]

    outcome: str = browser.wait_for_outcome(
        mock_page,
        "https://portal.example.com/home",
        blocked_texts=["no lo podemos atender"],
    )

    assert outcome == browser.OUTCOME_SUCCESS


def test_wait_for_outcome_blocked_clears_then_times_out(
    mock_page: mock.MagicMock,
) -> None:
    blocked_handle = mock.MagicMock()
    blocked_handle.json_value.return_value = browser.OUTCOME_BLOCKED
    mock_page.wait_for_function.side_effect = [
        blocked_handle,
        TimeoutError(""),
        TimeoutError(""),
    ]

    with pytest.raises(TimeoutError):
        browser.wait_for_outcome(
            mock_page,
            "https://portal.example.com/home",
            blocked_texts=["no lo podemos atender"],
        )


def test_wait_for_outcome_timeout(mock_page: mock.MagicMock) -> None:
    mock_page.wait_for_function.side_effect = TimeoutError("")

    with pytest.raises(TimeoutError):
        browser.wait_for_outcome(
            mock_page, "https://portal.example.com/home", timeout=1000.0
        )

    assert mock_page.wait_for_function.call_args.kwargs["timeout"] == pytest.approx(
        1000.0, abs=100
    )
