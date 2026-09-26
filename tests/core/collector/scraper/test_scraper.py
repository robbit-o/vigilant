from pathlib import Path
from typing import Type
from unittest import mock

import pytest
from playwright.sync_api import TimeoutError

from vigilant.common.browser import OUTCOME_BLOCKED, OUTCOME_ERROR, OUTCOME_SUCCESS
from vigilant.common.exceptions import LoginBlocked, LoginRejected
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


def test_wait_for_login(
    mock_scraper: Type[Scraper],
    mock_page: mock.MagicMock,
) -> None:
    mock_page.wait_for_function.return_value.json_value.return_value = OUTCOME_SUCCESS

    mock_scraper(mock_page)._wait_for_login(
        "https://portal.example.com/home", error_text="datos incorrectos"
    )

    assert mock_page.wait_for_function.call_args.kwargs["arg"] == [
        "https://portal.example.com/home",
        "",
        "datos incorrectos",
        [],
        None,
    ]


def test_wait_for_login_blocked(
    mock_scraper: Type[Scraper],
    mock_page: mock.MagicMock,
) -> None:
    mock_page.url = "https://www.example.com/"
    mock_page.wait_for_function.return_value.json_value.return_value = OUTCOME_BLOCKED

    with pytest.raises(LoginBlocked) as block:
        mock_scraper(mock_page)._wait_for_login(
            "https://portal.example.com/home",
            blocked_texts=["no lo podemos atender"],
        )

    assert mock_page.wait_for_function.call_args.kwargs["arg"] == [
        "https://portal.example.com/home",
        "",
        "",
        ["no lo podemos atender"],
        None,
    ]
    assert "https://www.example.com/" in str(block.value)


def test_wait_for_login_rejected(
    mock_scraper: Type[Scraper],
    mock_page: mock.MagicMock,
) -> None:
    mock_page.wait_for_function.return_value.json_value.return_value = OUTCOME_ERROR

    with pytest.raises(LoginRejected) as rejection:
        mock_scraper(mock_page)._wait_for_login(
            "https://portal.example.com/home", error_text="datos incorrectos"
        )

    assert "datos incorrectos" in str(rejection.value)


def test_wait_for_login_rejected_by_selector(
    mock_scraper: Type[Scraper],
    mock_page: mock.MagicMock,
) -> None:
    mock_page.url = "https://www.example.com/"
    mock_page.wait_for_function.return_value.json_value.return_value = OUTCOME_ERROR

    with pytest.raises(LoginRejected) as rejection:
        mock_scraper(mock_page)._wait_for_login(
            "https://portal.example.com/home",
            error_selector="#login [role='alert']",
        )

    assert "https://www.example.com/" in str(rejection.value)


def test_wait_for_login_timeout(
    mock_scraper: Type[Scraper],
    mock_page: mock.MagicMock,
) -> None:
    mock_page.locator.return_value.inner_text.return_value = "Hesitation is defeat!"
    mock_page.wait_for_function.side_effect = TimeoutError("")

    with pytest.raises(LoginRejected) as rejection:
        mock_scraper(mock_page)._wait_for_login("https://portal.example.com/home")

    mock_page.locator.assert_called_once_with("body")
    assert "portal not reached" in str(rejection.value)
