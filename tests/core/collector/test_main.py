from typing import Type

import pytest

from vigilant.core.collector import main as collector
from vigilant.core.collector.scraper.scraper import Scraper


@pytest.fixture
def mock_scraper() -> Type[Scraper]:
    class MockScraper(Scraper):
        def navigate(self): ...

    return MockScraper


def test_get_enabled_scrapers(
    monkeypatch: pytest.MonkeyPatch,
    mock_scraper: Type[Scraper],
) -> None:
    monkeypatch.setattr(
        "vigilant.common.values.collector.ENABLED_SCRAPERS", ["MockScraper"]
    )

    collector.SCRAPER_REGISTRY = {"MockScraper": mock_scraper}

    enabled_scrapers = collector.get_enabled_scrapers()

    assert enabled_scrapers == {"MockScraper": mock_scraper}
