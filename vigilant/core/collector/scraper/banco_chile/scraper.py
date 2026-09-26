from contextlib import suppress
from typing import Final

import pandas as pd
from playwright.sync_api import Locator, TimeoutError

from vigilant.common.browser import click_like_human, fill_like_human
from vigilant.common.models import AccountData, Transaction
from vigilant.common.spreadsheet import SpreadSheet
from vigilant.common.values import (
    finances_spreadsheet,
    settings,
)
from vigilant.core.collector.scraper.banco_chile.values import (
    secrets,
    Locators,
    IOResources,
)
from vigilant.core.collector.scraper import Scraper


class BancoChileScraper(Scraper):
    amount: int
    identifier: Final[str] = "Chile"

    def navigate(self) -> None:
        self._login()
        self._get_current_amount()
        self._get_credit_transactions()

    def _login(self) -> None:
        """Login to Web portal"""
        self.logger.info("Logging in ...")

        self.page.goto(secrets.LOGIN_URL)
        self.page.locator(Locators.USER_INPUT_ID).wait_for(
            state="visible", timeout=settings.BROWSER_WAIT_TIMEOUT
        )

        fill_like_human(
            self.page, Locators.USER_INPUT_ID, secrets.USERNAME, numeric_only=True
        )
        fill_like_human(self.page, Locators.PASSWORD_INPUT_ID, secrets.PASSWORD)
        click_like_human(self.page, Locators.LOGIN_BTN_ID)

        self._wait_for_login(secrets.HOME_URL, error_text=Locators.LOGIN_ERROR_TEXT)

    def _get_current_amount(self) -> None:
        """Collect current account amount and save it in a file"""
        BANNER_WAIT_TIMEOUT: float = 3000.0

        self.logger.info("Getting current amount ...")

        with suppress(TimeoutError):
            self.page.locator(Locators.PROMOTION_BANNER_CLASS).wait_for(
                timeout=BANNER_WAIT_TIMEOUT
            )
            self.page.keyboard.press("Escape")

        self.amount = int(
            self.page.locator(Locators.AMOUNT_TEXT_CLASS)
            .first.text_content()
            .replace(".", "")
            .replace("$", "")
            .strip()
        )

    def _get_credit_transactions(self) -> None:
        """Collect current transactions on credit card"""
        self.logger.info("Getting transactions ...")

        self.page.goto(secrets.CREDIT_TRANSACTIONS_URL)

        download_group_btn: Locator = self.page.locator(
            Locators.DOWNLOAD_GROUP_BTN_XPATH
        )
        no_transactions: Locator = self.page.locator(Locators.NO_TRANSACTIONS_CLASS)

        # Either the movements table or the empty state shows up, so waiting for
        # both in turn would idle through a timeout before noticing the second
        no_transactions.or_(download_group_btn).first.wait_for(
            state="visible", timeout=settings.BROWSER_WAIT_TIMEOUT
        )

        if not download_group_btn.first.is_visible():
            self.logger.info("No transactions to download")
            return

        download_group_btn.click()

        with self.page.expect_download() as download_info:
            self.page.locator(Locators.DOWNLOAD_BTN_XPATH).click()

        download_info.value.save_as(self.data_path / IOResources.TRANSACTIONS_FILENAME)

    def export(self) -> AccountData:
        """Structure and returns collected data"""
        self.logger.info("Exporting data ...")

        transactions_file = self.data_path / IOResources.TRANSACTIONS_FILENAME
        collected_transactions: list[Transaction] = []
        if transactions_file.exists():
            TRANSACTIONS_COLUMNS_INDEX: tuple[str] = (1, 4, 6, 10)
            TRANSACTIONS_COLUMNS_KEYS: tuple[str] = (
                "date",
                "description",
                "location",
                "amount",
            )

            transactions: pd.DataFrame = pd.read_excel(
                transactions_file,
                sheet_name=0,
                header=17,
                names=TRANSACTIONS_COLUMNS_KEYS,
                usecols=TRANSACTIONS_COLUMNS_INDEX,
            )

            spreadsheet = SpreadSheet.load(finances_spreadsheet.KEY)
            payment_descriptions: list[str] = [
                desc.pop()
                for desc in spreadsheet.read(
                    finances_spreadsheet.DATA_WORKSHEET_NAME,
                    finances_spreadsheet.PAYMENT_DESC_RANGE,
                )
            ]

            transactions = transactions[
                (~transactions.description.isin(payment_descriptions))
            ].fillna("")

            transactions = transactions.iloc[:, [0, 3, 1, 2]]

            collected_transactions = [
                Transaction(
                    **dict(zip(list(Transaction.model_fields), raw_transaction))
                )
                for raw_transaction in transactions.values.tolist()
            ]

        return AccountData(
            identifier=self.identifier,
            amount=self.amount,
            transactions=collected_transactions,
        )
