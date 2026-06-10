from pathlib import Path
from typing import Type
from unittest import mock

import pytest

from vigilant.core.collector.scraper.scraper import Scraper


@pytest.fixture
def mock_scraper() -> Type[Scraper]:
    class MockScraper(Scraper):
        navigate = mock.MagicMock()
        export = mock.MagicMock()

    return MockScraper


def test_scrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_scraper: Type[Scraper],
) -> None:
    monkeypatch.setattr("vigilant.common.values.IOResources.DATA_PATH", tmp_path)
    monkeypatch.setattr(
        "vigilant.common.values.collector.ENABLED_SCRAPERS", ["MockScraper"]
    )

    mock_scraper_instance = mock_scraper(mock.MagicMock())
    mock_scraper_instance.scrap()

    assert isinstance(mock_scraper_instance.data_path, Path)
    assert mock_scraper_instance.data_path.exists()
    assert mock_scraper_instance.logger is not None
    assert mock_scraper_instance.logger.extra == {
        "role": "Scraper",
        "entity": "MockScraper",
    }
    mock_scraper_instance.navigate.assert_called_once()
    mock_scraper_instance.export.assert_called_once()
