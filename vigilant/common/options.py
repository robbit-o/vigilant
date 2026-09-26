from dataclasses import dataclass
from typing import Final, Optional

from vigilant import logger
from vigilant.common.values import settings

DEFAULT_WIDTH: Final[int] = 1920
DEFAULT_HEIGHT: Final[int] = 1080

WINDOW_SCALE: Final[float] = 0.8
ASPECT_RATIO: Final[float] = 16 / 9


@dataclass(frozen=True)
class BrowserOptions:
    """Browser window configuration resolved from the command line.

    Attributes:
        headless (bool): Whether the browser window is hidden
        width (int): Window width in pixels
        height (int): Window height in pixels
        record_video (bool): Whether the browser session is recorded
    """

    headless: bool = True
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    record_video: bool = settings.BROWSER_RECORD_VIDEO

    @property
    def viewport(self) -> dict[str, int]:
        """Page viewport size

        Returns:
            dict[str, int]: Width and height in pixels
        """
        return {"width": self.width, "height": self.height}


def build_browser_options(
    show_window: bool = False,
    width: Optional[int] = None,
    height: Optional[int] = None,
    record_video: Optional[bool] = None,
) -> BrowserOptions:
    """Resolves browser options from the command line parameters.

    A visible window defaults to a slightly reduced 16:9 size to fit the screen
    chrome, otherwise the full 16:9 size is used. When only one dimension is
    given, the other one is derived from the 16:9 aspect ratio. Video recording
    falls back to the environment configuration when not given.

    Args:
        show_window (bool): Whether the browser window is shown
        width (Optional[int]): Window width in pixels
        height (Optional[int]): Window height in pixels
        record_video (Optional[bool]): Whether the browser session is recorded,
            `None` keeps the environment configuration

    Returns:
        BrowserOptions: Resolved browser options
    """
    if not width and not height:
        width = _scale(DEFAULT_WIDTH) if show_window else DEFAULT_WIDTH
        height = _scale(DEFAULT_HEIGHT) if show_window else DEFAULT_HEIGHT
    elif width and not height:
        height = _from_width(width)
    elif height and not width:
        width = _from_height(height)

    options: BrowserOptions = BrowserOptions(
        headless=not show_window,
        width=width,
        height=height,
        record_video=(
            settings.BROWSER_RECORD_VIDEO if record_video is None else record_video
        ),
    )

    if not _is_16_9(options.width, options.height):
        logger.warning(
            f"Window size {options.width}x{options.height} does not keep the 16:9 ratio"
        )

    return options


def configure(options: BrowserOptions) -> None:
    """Applies browser options to the current runtime configuration.

    Args:
        options (BrowserOptions): Browser options to apply
    """
    global current

    current = options


def _scale(size: int) -> int:
    return _to_even(size * WINDOW_SCALE)


def _from_width(width: int) -> int:
    return _to_even(width / ASPECT_RATIO)


def _from_height(height: int) -> int:
    return _to_even(height * ASPECT_RATIO)


def _to_even(size: float) -> int:
    return int(round(size / 2)) * 2


def _is_16_9(width: int, height: int) -> bool:
    return abs(width / height - ASPECT_RATIO) < 0.01


current: BrowserOptions = BrowserOptions()
