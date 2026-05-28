from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

from vigilant import logger
from vigilant.common.browser import session
from vigilant.common.models import AccountData, BankSheetConfig
from vigilant.common.spreadsheet import SpreadSheet
from vigilant.common.values import finances_spreadsheet
from vigilant.core.collector import Scraper as SRP

TRANSACTIONS_COUNT: Final[int] = 100


class SyncService:
    def __init__(self, Scraper: type[SRP], sheet_config: BankSheetConfig):
        self.Scraper = Scraper
        self.sheet_config = sheet_config

    def sync_bank(self):
        with session() as page:
            scraper = self.Scraper(page)
            scraper.scrap()

        if scraper.account_data:
            self.upload_finances(scraper.account_data)

    def upload_finances(self, account_data: AccountData) -> None:
        logger.info("Updating spreadsheet ...")

        spreadsheet = SpreadSheet.load(finances_spreadsheet.KEY)

        transactions = [trx.to_list() for trx in account_data.transactions]
        transactions.extend(
            [["", "", "", ""]] * (TRANSACTIONS_COUNT - len(transactions))
        )

        spreadsheet.write(
            self.sheet_config.worksheet,
            self.sheet_config.amount_cell,
            [[account_data.amount]],
        )
        spreadsheet.write(
            self.sheet_config.worksheet,
            self.sheet_config.transactions_cell,
            transactions,
        )

        spreadsheet.write(
            self.sheet_config.worksheet,
            self.sheet_config.update_dateime_cell,
            [
                [
                    datetime.now(ZoneInfo("America/Santiago")).strftime(
                        "%Y/%m/%d %H:%M:%S"
                    )
                ]
            ],
        )
