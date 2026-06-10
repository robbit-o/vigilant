from unittest import mock

from vigilant.common.models import AccountData, BankSheetConfig, Transaction
from vigilant.common.values import finances_spreadsheet
from vigilant.run import SyncService


@mock.patch("vigilant.core.main.SpreadSheet")
def test_upload_finances(MockSpreadSheet: mock.MagicMock) -> None:
    mock_spreadsheet = mock.MagicMock()
    MockSpreadSheet.load.return_value = mock_spreadsheet

    sheet_config = BankSheetConfig(
        worksheet="Data",
        amount_cell="E4",
        transactions_cell="D7",
        update_dateime_cell="E2",
    )

    account_data = AccountData(
        identifier="BancoChile",
        amount=1000,
        transactions=[
            Transaction(date="31/12/1999", description="store", location="", amount=100)
        ],
    )

    service = SyncService(mock.MagicMock(), sheet_config)
    service.upload_finances(account_data)

    MockSpreadSheet.load.assert_called_once_with(finances_spreadsheet.KEY)
    assert mock_spreadsheet.write.call_count == 3

    amount_args = mock_spreadsheet.write.call_args_list[0][0]
    transactions_args = mock_spreadsheet.write.call_args_list[1][0]

    assert amount_args[1] == "E4"
    assert amount_args[2] == [[1000]]
    assert transactions_args[1] == "D7"
    assert transactions_args[2][0] == ["31/12/1999", 100, "store", ""]
    assert len(transactions_args[2]) == 100


@mock.patch("vigilant.core.main.session")
def test_sync_bank_calls_upload_finances(
    mock_session: mock.MagicMock,
) -> None:
    mock_page = mock.MagicMock()
    mock_session.return_value.__enter__.return_value = mock_page

    mock_scraper_instance = mock.MagicMock()
    mock_scraper_instance.account_data = AccountData(
        identifier="BancoChile",
        amount=123,
        transactions=[
            Transaction(date="01/01/2024", description="store", location="", amount=50)
        ],
    )
    mock_scraper_instance.scrap = mock.MagicMock()

    mock_scraper_cls = mock.MagicMock(return_value=mock_scraper_instance)
    sheet_config = BankSheetConfig(
        worksheet="Data",
        amount_cell="E4",
        transactions_cell="D7",
        update_dateime_cell="E2",
    )

    service = SyncService(mock_scraper_cls, sheet_config)
    service.upload_finances = mock.MagicMock()

    service.sync_bank()

    mock_session.assert_called_once()
    mock_scraper_cls.assert_called_once_with(mock_page)
    mock_scraper_instance.scrap.assert_called_once()
    service.upload_finances.assert_called_once_with(mock_scraper_instance.account_data)


@mock.patch("vigilant.core.main.session")
def test_sync_bank_skips_upload_when_no_account_data(
    mock_session: mock.MagicMock,
) -> None:
    mock_page = mock.MagicMock()
    mock_session.return_value.__enter__.return_value = mock_page

    mock_scraper_instance = mock.MagicMock()
    mock_scraper_instance.account_data = None
    mock_scraper_instance.scrap = mock.MagicMock()

    mock_scraper_cls = mock.MagicMock(return_value=mock_scraper_instance)
    sheet_config = BankSheetConfig(
        worksheet="Data",
        amount_cell="E4",
        transactions_cell="D7",
        update_dateime_cell="E2",
    )

    service = SyncService(mock_scraper_cls, sheet_config)
    service.upload_finances = mock.MagicMock()

    service.sync_bank()

    service.upload_finances.assert_not_called()
