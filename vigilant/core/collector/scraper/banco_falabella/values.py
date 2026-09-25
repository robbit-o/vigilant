from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FALABELLA_",
        extra="ignore",
    )

    USERNAME: str
    PASSWORD: str

    LOGIN_URL: str
    HOME_URL: str


secrets = Secrets()


class Locators:
    USER_INPUT_ID: Final[str] = "#document"
    PASSWORD_INPUT_ID: Final[str] = "#pass"
    PRODUCT_BTN_ID: Final[str] = "#cardDetail0"

    PRODUCT_BTN_CLASS: Final[str] = ".div-product"
    DOWNLOAD_BTN_CLASS: Final[str] = ".btn-doc-export"
    CLOSE_BANNER_BTN_CLASS: Final[str] = ".close-button"

    LOGIN_FORM_BTN_XPATH: Final[str] = (
        '//*[@id="main-header"]/nav[2]/div/div/div[2]/button'
    )
    LOGIN_SUBMIT_BTN_XPATH: Final[str] = (
        '//*[@id="drawer"]/div[2]/div/div/div[1]/form/div[2]/button'
    )
    PROMOTION_BANNER_XPATH: Final[str] = '//*[@id="shadow-container"]'


class IOResources:
    TRANSACTIONS_FILENAME: Final[str] = "transactions.xls"
    OUTPUT_FILENAME: Final[str] = "banco_falabella.json"
