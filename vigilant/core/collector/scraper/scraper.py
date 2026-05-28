import random
import string
from abc import ABC, abstractmethod
from pathlib import Path

from playwright.sync_api import Page

from vigilant.common.models import AccountData
from vigilant.common.values import IOResources
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

    @abstractmethod
    def navigate(self) -> None: ...

    @abstractmethod
    def export(self) -> AccountData: ...
