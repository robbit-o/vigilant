import pytest

from vigilant.common import options


@pytest.fixture(autouse=True)
def reset_options() -> None:
    options.configure(options.BrowserOptions())


@pytest.mark.parametrize(
    ("show_window", "width", "height", "expected"),
    [
        (False, None, None, options.BrowserOptions(True, 1920, 1080)),
        (False, 1280, 720, options.BrowserOptions(True, 1280, 720)),
        (False, 1280, None, options.BrowserOptions(True, 1280, 720)),
        (False, None, 720, options.BrowserOptions(True, 1280, 720)),
        (True, None, None, options.BrowserOptions(False, 1536, 864)),
        (True, 1280, 720, options.BrowserOptions(False, 1280, 720)),
        (True, 1280, None, options.BrowserOptions(False, 1280, 720)),
        (True, None, 900, options.BrowserOptions(False, 1600, 900)),
        (True, 1000, 1000, options.BrowserOptions(False, 1000, 1000)),
    ],
)
def test_build_browser_options(
    show_window: bool,
    width: int | None,
    height: int | None,
    expected: options.BrowserOptions,
) -> None:
    assert options.build_browser_options(show_window, width, height) == expected


def test_browser_options_defaults() -> None:
    assert options.current == options.BrowserOptions()


def test_browser_options_viewport() -> None:
    assert options.BrowserOptions(width=800, height=600).viewport == {
        "width": 800,
        "height": 600,
    }


def test_configure() -> None:
    browser_options: options.BrowserOptions = options.build_browser_options(
        show_window=True, width=1024
    )

    options.configure(browser_options)

    assert options.current == browser_options
