import json
from pathlib import Path
from typing import Any
from unittest import mock

import pandas as pd
import pytest
from playwright.sync_api import TimeoutError

from vigilant.common.browser import OUTCOME_SUCCESS
from vigilant.core.collector.scraper.banco_falabella.scraper import BUTTON_HOLD_MS
from vigilant.core.collector.scraper.banco_falabella.values import (
    secrets,
    Locators,
    BLOCKED_TEXT_FRAGMENTS,
    IOResources,
)
from vigilant.core.collector.scraper import BancoFalabellaScraper


@pytest.fixture
def mock_bank_falabella_data() -> dict:
    return json.loads(Path("tests/resources/bank_falabella.json").read_text())


@mock.patch("vigilant.core.collector.scraper.BancoFalabellaScraper._login")
@mock.patch(
    "vigilant.core.collector.scraper.BancoFalabellaScraper._get_credit_transactions"
)
def test_navigate(
    _get_credit_transactions: mock.MagicMock,
    _login: mock.MagicMock,
    mock_page: mock.MagicMock,
) -> None:
    scraper = BancoFalabellaScraper(mock_page)
    scraper.navigate()

    _login.assert_called_once()
    _get_credit_transactions.assert_called_once()


@mock.patch("vigilant.core.collector.scraper.banco_falabella.scraper.click_like_human")
@mock.patch("vigilant.core.collector.scraper.banco_falabella.scraper.fill_like_human")
def test_login(
    mock_fill_like_human: mock.MagicMock,
    mock_click_like_human: mock.MagicMock,
    mock_page: mock.MagicMock,
) -> None:
    mock_page.wait_for_function.return_value.json_value.return_value = OUTCOME_SUCCESS

    BancoFalabellaScraper(mock_page)._login()

    mock_page.goto.assert_called_once_with(secrets.LOGIN_URL)
    mock_page.locator.assert_any_call(Locators.LOGIN_FORM_BTN_XPATH)
    mock_page.locator.assert_any_call(Locators.USER_INPUT_ID)
    mock_page.locator.assert_any_call(Locators.LOGIN_SUBMIT_BTN_XPATH)
    assert mock_page.locator.return_value.wait_for.call_count == 3

    mock_fill_like_human.assert_any_call(
        mock_page, Locators.USER_INPUT_ID, secrets.USERNAME, numeric_only=True
    )
    mock_fill_like_human.assert_any_call(
        mock_page, Locators.PASSWORD_INPUT_ID, secrets.PASSWORD
    )
    mock_click_like_human.assert_any_call(
        mock_page, Locators.LOGIN_FORM_BTN_XPATH, hold=BUTTON_HOLD_MS
    )
    mock_click_like_human.assert_any_call(
        mock_page, Locators.LOGIN_SUBMIT_BTN_XPATH, hold=BUTTON_HOLD_MS
    )
    assert mock_page.wait_for_function.call_args.kwargs["arg"] == [
        secrets.HOME_URL,
        Locators.LOGIN_ERROR_SELECTOR,
        "",
        BLOCKED_TEXT_FRAGMENTS,
        None,
    ]


def test_get_credit_transactions(tmp_path: Path, mock_page: mock.MagicMock) -> None:
    (tmp_path / IOResources.TRANSACTIONS_FILENAME).write_text("Hesitation is defeat!")

    mock_download_info = mock.MagicMock()
    mock_page.expect_download.return_value.__enter__.return_value = mock_download_info

    scraper = BancoFalabellaScraper(mock_page)
    scraper.data_path = tmp_path

    scraper._get_credit_transactions()

    mock_page.locator().wait_for.assert_called_once()
    mock_page.locator().click.assert_called()
    mock_download_info.value.save_as.assert_called_once_with(
        tmp_path / IOResources.TRANSACTIONS_FILENAME
    )


def test_get_credit_transactions_closes_late_banner(
    tmp_path: Path, mock_page: mock.MagicMock
) -> None:
    (tmp_path / IOResources.TRANSACTIONS_FILENAME).write_text("Hesitation is defeat!")

    mock_download_info = mock.MagicMock()
    mock_page.expect_download.return_value.__enter__.return_value = mock_download_info

    mock_locator = mock_page.locator.return_value
    click_calls: list[int] = []

    def mock_click(*_args: Any, **_kwargs: Any) -> None:
        click_calls.append(1)
        # the promotion modal appears after the first wait expired and blocks
        # the product button click
        if len(click_calls) == 2:
            raise TimeoutError("intercepts pointer events")

    mock_locator.click.side_effect = mock_click

    scraper = BancoFalabellaScraper(mock_page)
    scraper.data_path = tmp_path

    scraper._get_credit_transactions()

    # banner dismissed on the initial wait and again after the blocked click
    assert mock_locator.wait_for.call_count == 2
    # two banner closes, the blocked product click and its retry
    assert len(click_calls) == 4
    mock_download_info.value.save_as.assert_called_once_with(
        tmp_path / IOResources.TRANSACTIONS_FILENAME
    )


@mock.patch("vigilant.core.collector.scraper.banco_falabella.scraper.SpreadSheet")
@mock.patch("vigilant.core.collector.scraper.banco_falabella.scraper.pd.read_excel")
def test_export(
    mock_pd_read_excel: mock.MagicMock,
    MockSpreadSheet: mock.MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_page: mock.MagicMock,
    mock_bank_falabella_data: dict,
) -> None:
    mock_cols_keys: tuple[str] = ("date", "description", "fees", "amount")
    mock_cols_index: tuple[str] = (0, 1, 4, 5)

    mock_data: list[list[Any]] = [
        [pd.to_datetime("1999-12-31"), "Clothes", 0, 25000],
        [pd.to_datetime("1999-12-04"), "PAGO TARJETA CMR", 0, -120000],
        [pd.to_datetime("1999-12-24"), "Food", 0, 40000],
        [pd.to_datetime("1999-12-04"), "Shoes", 4, 33200],
    ]
    mock_data_df = pd.DataFrame(mock_data, columns=mock_cols_keys)

    mock_payment_description: list[list[str]] = [
        ["PAGO TARJETA CMR"],
    ]

    mock_pd_read_excel.return_value = mock_data_df

    mock_spreadsheet = mock.MagicMock()
    mock_spreadsheet.read.return_value = mock_payment_description
    MockSpreadSheet.load.return_value = mock_spreadsheet

    monkeypatch.setattr(
        "vigilant.common.values.IOResources.OUTPUT_PATH",
        tmp_path,
    )
    monkeypatch.setattr(
        "vigilant.core.collector.scraper.banco_falabella.values.IOResources.OUTPUT_FILENAME",
        "bank_data.json",
    )

    scraper = BancoFalabellaScraper(mock_page)
    scraper.data_path = Path("/")

    account_data = scraper.export()

    mock_pd_read_excel.assert_called_once_with(
        Path("/", IOResources.TRANSACTIONS_FILENAME),
        sheet_name=0,
        header=0,
        names=mock_cols_keys,
        usecols=mock_cols_index,
    )
    assert account_data.model_dump() == mock_bank_falabella_data
