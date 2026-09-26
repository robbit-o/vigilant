import random
import string
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page, TimeoutError

from vigilant.common.browser import OUTCOME_SUCCESS, OUTCOME_BLOCKED, wait_for_outcome
from vigilant.common.exceptions import LoginBlocked, LoginRejected
from vigilant.common.models import AccountData
from vigilant.common.values import settings, IOResources
from vigilant import logger
import logging


class Scraper(ABC):
    account_data: AccountData

    def __init__(self, page: Page):
        self.page = page
        self.data_path: Path = IOResources.DATA_PATH / "".join(
            random.choices((string.ascii_letters + string.digits), k=7)
        )

        scraper_name = self.__class__.__name__
        self.logger = logging.LoggerAdapter(
            logger.getChild(scraper_name), {"role": "Scraper", "entity": scraper_name}
        )

    def scrap(self) -> None:
        self.data_path.mkdir(parents=True, exist_ok=True)

        self.navigate()
        self.account_data = self.export()

    def _wait_for_login(
        self,
        success_url: str,
        error_selector: str = "",
        error_text: str = "",
        blocked_texts: Optional[list[str]] = None,
        blocked_url: Optional[str] = None,
    ) -> None:
        """Waits until the portal opens, the login form refuses the attempt, or
        an anti-bot screen refuses to serve the session.

        Args:
            success_url (str): URL the portal opens at once the login is accepted
            error_selector (str): Selector of a visible node that reports the
                rejection, empty when the form reports it as text
            error_text (str): Wording that reports the rejection
            blocked_texts (Optional[list[str]]): Wordings of a page that refuses
                to serve the session, empty to ignore them
            blocked_url (Optional[str]): URL substring of a block or challenge
                page, empty to ignore it

        Raises:
            LoginRejected: When the form refuses the credentials or the portal
                is never reached
            LoginBlocked: When an anti-bot or "try later" screen is served
        """
        self.logger.info("Waiting for the portal ...")

        try:
            outcome: str = wait_for_outcome(
                self.page,
                success_url,
                error_selector,
                error_text,
                blocked_texts,
                blocked_url,
            )
        except TimeoutError:
            self.logger.warning(
                f"Login did not complete, page shows: "
                f"{self.page.locator('body').inner_text()[:200]}"
            )
            raise LoginRejected(
                f"portal not reached after {settings.BROWSER_WAIT_TIMEOUT} ms"
            )

        if outcome == OUTCOME_BLOCKED:
            raise LoginBlocked(f"try later screen reported at {self.page.url}")

        if outcome != OUTCOME_SUCCESS:
            raise LoginRejected(error_text or f"rejection reported at {self.page.url}")

    @abstractmethod
    def navigate(self) -> None: ...

    @abstractmethod
    def export(self) -> AccountData: ...
