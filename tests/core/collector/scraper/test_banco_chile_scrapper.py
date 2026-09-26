import json
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import pandas as pd
from playwright.sync_api import TimeoutError

from vigilant.common.browser import OUTCOME_SUCCESS
from vigilant.common.values import settings
from vigilant.core.collector.scraper import BancoChileScraper
from vigilant.core.collector.scraper.banco_chile.values import (
    secrets,
    Locators,
    IOResources,
)


@pytest.fixture
def mock_bank_chile_data() -> dict:
    return json.loads(Path("tests/resources/bank_chile.json").read_text())


@pytest.fixture
def mock_bank_chile_no_transactions_data() -> dict:
    return json.loads(
        Path("tests/resources/bank_chile_no_transactions.json").read_text()
    )


@mock.patch("vigilant.core.collector.scraper.BancoChileScraper._login")
@mock.patch("vigilant.core.collector.scraper.BancoChileScraper._get_current_amount")
@mock.patch(
    "vigilant.core.collector.scraper.BancoChileScraper._get_credit_transactions"
)
def test_navigate(
    _get_credit_transactions: mock.MagicMock,
    _get_current_amount: mock.MagicMock,
    _login: mock.MagicMock,
    mock_page: mock.MagicMock,
) -> None:
    scraper = BancoChileScraper(mock_page)
    scraper.navigate()

    _login.assert_called_once()
    _get_current_amount.assert_called_once()
    _get_credit_transactions.assert_called_once()


@mock.patch("vigilant.core.collector.scraper.banco_chile.scraper.click_like_human")
@mock.patch("vigilant.core.collector.scraper.banco_chile.scraper.fill_like_human")
def test_login(
    mock_fill_like_human: mock.MagicMock,
    mock_click_like_human: mock.MagicMock,
    mock_page: mock.MagicMock,
) -> None:
    mock_page.wait_for_function.return_value.json_value.return_value = OUTCOME_SUCCESS

    BancoChileScraper(mock_page)._login()

    mock_page.goto.assert_called_once_with(secrets.LOGIN_URL)
    mock_page.locator.assert_called_once_with(Locators.USER_INPUT_ID)
    mock_page.locator.return_value.wait_for.assert_called_once()
    mock_fill_like_human.assert_any_call(
        mock_page, Locators.USER_INPUT_ID, secrets.USERNAME, numeric_only=True
    )
    mock_fill_like_human.assert_any_call(
        mock_page, Locators.PASSWORD_INPUT_ID, secrets.PASSWORD
    )
    mock_click_like_human.assert_called_once_with(mock_page, Locators.LOGIN_BTN_ID)
    assert mock_page.wait_for_function.call_args.kwargs["arg"] == [
        secrets.HOME_URL,
        "",
        Locators.LOGIN_ERROR_TEXT,
        [],
        None,
    ]


def test_get_current_amount(
    mock_page: mock.MagicMock,
) -> None:
    mock_formatted_amount: str = " $1.000"
    mock_amount: int = 1000

    mock_page.locator.return_value.first.text_content.return_value = (
        mock_formatted_amount
    )

    scraper = BancoChileScraper(mock_page)
    scraper._get_current_amount()

    assert scraper.amount == mock_amount


def test_get_credit_transactions(tmp_path: Path, mock_page: mock.MagicMock) -> None:
    (tmp_path / IOResources.TRANSACTIONS_FILENAME).write_text("Hesitation is defeat!")

    mock_download_info = mock.MagicMock()
    mock_page.expect_download.return_value.__enter__.return_value = mock_download_info
    mock_page.locator.return_value.first.is_visible.return_value = True

    scraper = BancoChileScraper(mock_page)
    scraper.data_path = tmp_path

    scraper._get_credit_transactions()

    mock_page.goto.assert_called_once()
    mock_page.locator().or_.assert_called_once()
    mock_page.locator().or_.return_value.first.wait_for.assert_called_once_with(
        state="visible", timeout=settings.BROWSER_WAIT_TIMEOUT
    )
    mock_page.locator().click.assert_called()
    mock_download_info.value.save_as.assert_called_once_with(
        tmp_path / IOResources.TRANSACTIONS_FILENAME
    )


def test_get_credit_transactions_empty(
    tmp_path: Path, mock_page: mock.MagicMock
) -> None:
    (tmp_path / IOResources.TRANSACTIONS_FILENAME).write_text("Hesitation is defeat!")

    mock_no_transactions, mock_download_group_btn = mock.MagicMock(), mock.MagicMock()

    def mock_locators(mock_selector: str) -> mock.MagicMock:
        if mock_selector == Locators.NO_TRANSACTIONS_CLASS:
            return mock_no_transactions
        return mock_download_group_btn

    mock_page.locator = mock.MagicMock(side_effect=mock_locators)
    mock_download_group_btn.first.is_visible.return_value = False

    scraper = BancoChileScraper(mock_page)
    scraper.data_path = tmp_path

    scraper._get_credit_transactions()

    mock_no_transactions.or_.assert_called_once_with(mock_download_group_btn)
    mock_no_transactions.or_.return_value.first.wait_for.assert_called_once()
    mock_download_group_btn.click.assert_not_called()
    mock_page.expect_download.assert_not_called()


def test_get_credit_transactions_nothing_visible(
    tmp_path: Path, mock_page: mock.MagicMock
) -> None:
    mock_no_transactions = mock.MagicMock()
    mock_no_transactions.or_.return_value.first.wait_for.side_effect = TimeoutError("")

    mock_page.locator = mock.MagicMock(
        side_effect=lambda selector: (
            mock_no_transactions
            if selector == Locators.NO_TRANSACTIONS_CLASS
            else mock.MagicMock()
        )
    )

    scraper = BancoChileScraper(mock_page)
    scraper.data_path = tmp_path

    with pytest.raises(TimeoutError):
        scraper._get_credit_transactions()

    mock_page.expect_download.assert_not_called()


@mock.patch("vigilant.core.collector.scraper.banco_chile.scraper.SpreadSheet")
@mock.patch("vigilant.core.collector.scraper.banco_chile.scraper.pd.read_excel")
def test_export(
    mock_pd_read_excel: mock.MagicMock,
    MockSpreadSheet: mock.MagicMock,
    tmp_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    mock_page: mock.MagicMock,
    mock_bank_chile_data: dict,
) -> None:
    mock_data_path: Path = tmp_path_factory.mktemp("data")
    (mock_data_path / IOResources.TRANSACTIONS_FILENAME).write_text(
        "Hesitation is defeat!"
    )

    mock_cols_keys: tuple[str] = ("date", "description", "location", "amount")
    mock_cols_index: tuple[str] = (1, 4, 6, 10)

    mock_data: list[list[Any]] = [
        ["31/12/1999", "Clothes", "Santiago", 25000],
        ["04/12/1999", "TEF PAGO NORMAL", "Santiago", -120000],
        ["24/12/1999", "Food", None, 40000],
        ["04/12/1999", "Pago Pesos TAR", "Santiago", -88000],
    ]
    mock_data_df = pd.DataFrame(mock_data, columns=mock_cols_keys)

    mock_payment_description: list[list[str]] = [
        ["TEF PAGO NORMAL"],
        ["Pago Pesos TAR"],
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
        "vigilant.core.collector.scraper.banco_chile.values.IOResources.OUTPUT_FILENAME",
        "bank_data.json",
    )

    scraper = BancoChileScraper(mock_page)
    scraper.data_path = mock_data_path
    scraper.amount = 123456

    account_data = scraper.export()

    mock_pd_read_excel.assert_called_once_with(
        mock_data_path / IOResources.TRANSACTIONS_FILENAME,
        sheet_name=0,
        header=17,
        names=mock_cols_keys,
        usecols=mock_cols_index,
    )
    assert account_data.model_dump() == mock_bank_chile_data


def test_export_no_transactions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mock_page: mock.MagicMock,
    mock_bank_chile_no_transactions_data: dict,
) -> None:
    monkeypatch.setattr(
        "vigilant.common.values.IOResources.OUTPUT_PATH",
        tmp_path,
    )
    monkeypatch.setattr(
        "vigilant.core.collector.scraper.banco_chile.values.IOResources.OUTPUT_FILENAME",
        "bank_data.json",
    )

    scraper = BancoChileScraper(mock_page)
    scraper.data_path = Path("/")
    scraper.amount = 123456

    account_data = scraper.export()

    assert account_data.model_dump() == mock_bank_chile_no_transactions_data
