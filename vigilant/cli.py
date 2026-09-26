from typing import Optional

import typer

from vigilant import logger, run
from vigilant.common import options
from vigilant.common.values import collector
from vigilant.core.collector.main import SCRAPER_REGISTRY

app = typer.Typer(
    add_completion=False,
    help="Collect finances data and load it into a google spreadsheet",
)


@app.command()
def main(
    show_window: bool = typer.Option(
        False,
        "--show-window",
        help="Show the browser window, with a slightly reduced 16:9 size",
    ),
    width: Optional[int] = typer.Option(
        None, "-w", "--width", help="Browser window width in pixels"
    ),
    height: Optional[int] = typer.Option(
        None, "-h", "--height", help="Browser window height in pixels"
    ),
    scrapers: list[str] = typer.Option(
        [],
        "-s",
        "--scrapers",
        help="Enabled scrapers, e.g: -s BancoChile -s BancoFalabella",
    ),
    record_video: Optional[bool] = typer.Option(
        None,
        "--record-video/--no-record-video",
        help="Record the browser session, overrides the environment configuration",
    ),
) -> None:
    """Process for collecting finances data and load it into a google
    spreadsheet
    """
    _set_enabled_scrapers(scrapers)
    options.configure(
        options.build_browser_options(show_window, width, height, record_video)
    )

    run.main()


def _set_enabled_scrapers(scrapers: list[str]) -> None:
    """Overrides the enabled scrapers coming from the environment

    Args:
        scrapers (list[str]): Enabled scrapers, empty keeps the environment
            configuration

    Raises:
        typer.BadParameter: When a scraper is not registered
    """
    if not scrapers:
        logger.info(f"Enabled scrapers: {collector.ENABLED_SCRAPERS}")
        return

    enabled_scrapers: list[str] = [
        scraper.strip()
        for value in scrapers
        for scraper in value.split(",")
        if scraper.strip()
    ]

    unknown_scrapers: list[str] = [
        scraper for scraper in enabled_scrapers if scraper not in SCRAPER_REGISTRY
    ]

    if unknown_scrapers:
        raise typer.BadParameter(
            f"Unknown scrapers: {', '.join(unknown_scrapers)}. "
            f"Available scrapers: {', '.join(SCRAPER_REGISTRY)}"
        )

    collector.ENABLED_SCRAPERS = enabled_scrapers
    logger.info(f"Enabled scrapers: {collector.ENABLED_SCRAPERS}")


if __name__ == "__main__":
    app()
