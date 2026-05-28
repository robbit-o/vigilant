import json
from pathlib import Path
from typing import Any
from unittest import mock

import pandas as pd
import pytest

from vigilant.core.collector.scraper.banco_falabella.values import Locators, IOResources
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


def test_login(mock_page: mock.MagicMock) -> None:
    mock_login_btn, mock_user_input, mock_password_input, mock_generic_locator = (
        mock.MagicMock(),
        mock.MagicMock(),
        mock.MagicMock(),
        mock.MagicMock(),
    )

    def mock_login_form_locators(mock_selector: str = "") -> mock.MagicMock:
        match mock_selector:
            case Locators.LOGIN_FORM_BTN_XPATH:
                return mock_login_btn
            case Locators.USER_INPUT_XPATH:
                mock_locator = mock.MagicMock()
                mock_locator.first = mock_user_input
                return mock_locator
            case Locators.PASSWORD_INPUT_XPATH:
                mock_locator = mock.MagicMock()
                mock_locator.first = mock_password_input
                return mock_locator
            case Locators.PASSWORD_INPUT_XPATH:
                return mock_password_input
            case _:
                return mock_generic_locator

    mock_page.locator = mock.MagicMock(side_effect=mock_login_form_locators)

    BancoFalabellaScraper(mock_page)._login()

    mock_page.goto.assert_called_once()
    mock_page.wait_for_load_state()

    mock_login_btn.wait_for.assert_called_once()
    mock_login_btn.click.assert_called_once()

    mock_user_input.wait_for.assert_called_once()
    mock_user_input.fill.assert_called_once()

    mock_password_input.wait_for.assert_called_once()
    mock_password_input.fill.assert_called_once()

    mock_generic_locator.first.click.assert_called_once()
    mock_page.wait_for_url.assert_called_once()


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
