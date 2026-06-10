from unittest import mock

from vigilant.common import spreadsheet


@mock.patch("vigilant.common.spreadsheet.google.auth")
@mock.patch("vigilant.common.spreadsheet.gspread")
def test_load(mock_gspread: mock.MagicMock, mock_google_auth: mock.MagicMock) -> None:
    mock_google_auth.default.return_value = ("A", "B")
    spreadsheet_key = "ABC123"

    spreadsheet.SpreadSheet.load(spreadsheet_key)

    mock_google_auth.default.assert_called_once()
    mock_gspread.authorize.assert_called_once_with("A")
    mock_gspread.authorize().open_by_key.assert_called_once_with(spreadsheet_key)


def test_read() -> None:
    mock_title = "Hesitation"
    mock_range = "Defeat"
    mock_data = [["A"], ["B"], ["C"]]

    mock_worksheet = mock.MagicMock()
    mock_worksheet.get.return_value = mock_data

    _mock_spreadsheet = mock.MagicMock()
    _mock_spreadsheet.worksheet.return_value = mock_worksheet

    data: list[list[str]] = spreadsheet.SpreadSheet(_mock_spreadsheet).read(
        mock_title, mock_range
    )

    assert data == mock_data

    _mock_spreadsheet.worksheet.assert_called_once_with(mock_title)
    mock_worksheet.get.assert_called_once_with(mock_range)


def test_write() -> None:
    mock_title = "Hesitation"
    mock_range = "Defeat"
    mock_data = [["A"], ["B"], ["C"]]

    mock_worksheet = mock.MagicMock()
    _mock_spreadsheet = mock.MagicMock()
    _mock_spreadsheet.worksheet.return_value = mock_worksheet

    spreadsheet.SpreadSheet(_mock_spreadsheet).write(mock_title, mock_range, mock_data)

    _mock_spreadsheet.worksheet.assert_called_once_with(mock_title)
    mock_worksheet.update.assert_called_once_with(
        mock_data, mock_range, value_input_option="USER_ENTERED"
    )
