import json
from pathlib import Path
from typing import Final

from vigilant import logger
from vigilant.common.models import AccountData, AccountReport
from vigilant.common.spreadsheet import SpreadSheet
from vigilant.common.values import finances_spreadsheet, IOResources

TRANSACTIONS_COUNT: Final[int] = 198


def main() -> None:
    """Load transactions data into a google spreadsheet"""
    spreadsheet = SpreadSheet.load(finances_spreadsheet.KEY)

    upload_finances_data(spreadsheet, *load_finances_data())


def load_finances_data() -> tuple[int, list[list[str, int]]]:
    """Loads finances data from scrapers output

    Returns:
        tuple[int, list[list[str, int]]]: Accounts amount and transactions list
    """
    files = Path(IOResources.OUTPUT_PATH).glob("*.json")
    report = AccountReport(
        accounts=[AccountData(**json.loads(file.read_text())) for file in files]
    )

    return report.amount, report.transactions


def upload_finances_data(
    spreadsheet: SpreadSheet, account_amount: str, transactions: list[list[str]]
) -> None:
    """Uploads finances data into a google spreadsheet

    Args:
        spreadsheet (SpreadSheet): spreadsheet instance
        account_amount (str): Account amount
        transactions (list[list[str]]): transactions list
    """
    logger.info("Updating spreadsheet ...")

    transactions.extend(
        [["-", "", "", "", ""]] * (TRANSACTIONS_COUNT - len(transactions))
    )

    spreadsheet.write(
        finances_spreadsheet.FINANCES_WORKSHEET_NAME,
        finances_spreadsheet.AMOUNT_CELL,
        [[account_amount]],
    )
    spreadsheet.write(
        finances_spreadsheet.FINANCES_WORKSHEET_NAME,
        finances_spreadsheet.TRANSACTIONS_CELL,
        transactions,
    )


if __name__ == "__main__":
    main()
