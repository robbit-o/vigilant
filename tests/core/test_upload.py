import json
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from vigilant.core import upload
from vigilant.common.values import finances_spreadsheet


@pytest.fixture
def transformed_data_output() -> dict:
    return json.loads(Path("tests/resources/transformed_bank_data.json").read_text())


@mock.patch("vigilant.core.upload.SpreadSheet")
@mock.patch("vigilant.core.upload.upload_finances_data")
def test_main(
    upload_finances_data: mock.MagicMock,
    MockSpreadSheet: mock.MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_amount: int = 1000
    mock_transactions: list[list[Any]] = [["store", 100]]

    mock_spreadsheet = mock.MagicMock()
    MockSpreadSheet.load.return_value = mock_spreadsheet

    monkeypatch.setattr(
        "vigilant.core.upload.load_finances_data",
        lambda: (mock_amount, mock_transactions),
    )

    upload.main()

    MockSpreadSheet.load.assert_called_once_with(finances_spreadsheet.KEY)
    upload_finances_data.assert_called_once_with(
        mock_spreadsheet, mock_amount, mock_transactions
    )


def test_load_finances_data(
    monkeypatch: pytest.MonkeyPatch, transformed_data_output: dict
) -> None:
    monkeypatch.setattr(
        "vigilant.common.values.IOResources.OUTPUT_PATH",
        Path("tests/resources/scraper_output"),
    )

    amount, transactions = upload.load_finances_data()

    assert amount == transformed_data_output["amount"]
    assert sorted(transactions) == sorted(transformed_data_output["transactions"])


@mock.patch("vigilant.core.upload.SpreadSheet")
def test_upload_finances_data(MockSpreadSheet: mock.MagicMock) -> None:
    mock_spreadsheet = mock.MagicMock()
    MockSpreadSheet.load.return_value = mock_spreadsheet

    initial_transactions = [["store", 100], ["restaurant", 50]]
    upload.upload_finances_data(mock_spreadsheet, 1000, initial_transactions)

    calls = mock_spreadsheet.write.call_args_list
    transactions_call = calls[1]
    written_transactions = transactions_call[0][2]

    assert len(written_transactions) == upload.TRANSACTIONS_COUNT
    assert ["store", 100] in written_transactions
    assert ["restaurant", 50] in written_transactions
