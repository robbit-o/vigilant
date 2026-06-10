from contextlib import suppress
from typing import Final

import pandas as pd
from playwright.sync_api import Locator, TimeoutError

from vigilant.common.models import AccountData, Transaction
from vigilant.common.spreadsheet import SpreadSheet
from vigilant.common.values import (
    finances_spreadsheet,
    IOResources as VigilantIOResources,
)
from vigilant.core.collector.scraper.banco_falabella.values import (
    secrets,
    Locators,
    IOResources,
)
from vigilant.core.collector.scraper import Scraper


class BancoFalabellaScraper(Scraper):
    identifier: Final[str] = "Falabella"

    def navigate(self) -> None:
        self._login()
        self._get_credit_transactions()
        self._save()

    def _login(self) -> None:
        """Login to Web portal"""
        self.logger.info("Logging in ...")

        self.page.goto(secrets.LOGIN_URL)

        login_btn: Locator = self.page.locator(Locators.LOGIN_FORM_BTN_XPATH)
        login_btn.wait_for(state="visible")
        login_btn.click(delay=500.0)

        user_input: Locator = self.page.locator(Locators.USER_INPUT_XPATH).first
        user_input.wait_for(state="visible")
        user_input.fill(secrets.USERNAME)

        password_input: Locator = self.page.locator(Locators.PASSWORD_INPUT_XPATH).first
        password_input.wait_for(state="visible")
        password_input.fill(secrets.PASSWORD)

        submit_btn = self.page.locator(Locators.LOGIN_SUBMIT_BTN_ID).first
        submit_btn.wait_for(state="visible")
        submit_btn.click(delay=500.0)

        self.page.wait_for_url(secrets.HOME_URL)

    def _get_credit_transactions(self) -> None:
        """Collect current transactions on credit card"""
        BANNER_WAIT_TIMEOUT: float = 3000.0

        self.logger.info("Getting transactions ...")

        with suppress(TimeoutError):
            self.page.locator(Locators.PROMOTION_BANNER_XPATH).wait_for(
                timeout=BANNER_WAIT_TIMEOUT
            )
            self.page.locator(Locators.CLOSE_BANNER_BTN_CLASS).click()

        self.page.locator(Locators.PRODUCT_BTN_CLASS).click()

        with self.page.expect_download() as download_info:
            self.page.locator(Locators.DOWNLOAD_BTN_CLASS).first.click()

        download_info.value.save_as(self.data_path / IOResources.TRANSACTIONS_FILENAME)

    def _save(self) -> None:
        """Structure and saves collected data in a json file"""
        self.logger.info("Saving data ...")

        TRANSACTIONS_COLUMNS_INDEX: tuple[str] = (0, 1, 4, 5)
        TRANSACTIONS_COLUMNS_KEYS: tuple[str] = (
            "date",
            "description",
            "fees",
            "amount",
        )

        transactions: pd.DataFrame = pd.read_excel(
            self.data_path / IOResources.TRANSACTIONS_FILENAME,
            sheet_name=0,
            header=0,
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
            & (transactions.fees == 0)
        ].drop(columns=["fees"])
        transactions.insert(loc=2, column="location", value="")
        transactions["date"] = transactions["date"].dt.strftime("%d/%m/%Y")

        account_data = AccountData(
            identifier=self.identifier,
            amount=0,
            transactions=[
                Transaction(
                    **dict(zip(list(Transaction.model_fields), raw_transaction))
                )
                for raw_transaction in transactions.values.tolist()
            ],
        )

        (VigilantIOResources.OUTPUT_PATH / IOResources.OUTPUT_FILENAME).write_text(
            account_data.model_dump_json()
        )
