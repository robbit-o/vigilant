from __future__ import annotations

import google.auth
import gspread


class SpreadSheet:
    _spreadsheet: gspread.Spreadsheet

    def __init__(self, spreadsheet=gspread.Spreadsheet):
        self._spreadsheet = spreadsheet

    @staticmethod
    def load(key: str) -> SpreadSheet:
        """Login to GCP and returns an authorized spreadsheet instance

        Args:
            key (str): Unique key of the spreadsheet

        Returns:
            SpreadSheet: Authorized spreadsheet
        """
        scopes: list[str] = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials, _ = google.auth.default(scopes=scopes)
        gc: gspread.Client = gspread.authorize(credentials)

        return SpreadSheet(gc.open_by_key(key))

    def read(self, worksheet_title: str, range: str) -> list[list[str]]:
        """Reads from a range in a worksheet

        Args:
            worksheet_title (str): Title of the worksheet
            range (str): Location from where to read the data

        Returns:
            list[list[str]]: Data from the range
        """
        worksheet: gspread.Worksheet = self._spreadsheet.worksheet(worksheet_title)

        return worksheet.get(range)

    def write(self, worksheet_title, range: str, data: list[list[str]]) -> None:
        """Write data into a range of a worksheet

        Args:
            worksheet_title (str): Title of the worksheet
            range (str): Location from where to read the data
            data (list[list[str]]): Data to write in cells
        """
        worksheet: gspread.Worksheet = self._spreadsheet.worksheet(worksheet_title)

        worksheet.update(data, range, value_input_option="USER_ENTERED")
