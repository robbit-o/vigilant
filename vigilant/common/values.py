from pathlib import Path
from typing import Final, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    LOG_LEVEL: str = "INFO"
    BROWSER_WAIT_TIMEOUT: float = 30000.0
    STORAGE_LOCATION: str = "local"
    BUCKET_NAME: Optional[str] = None


class Collector(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENABLED_SCRAPERS: list[str] = ["BancoChile", "BancoFalabella"]


class FinancesSpreadsheet(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    KEY: str = "1IKyPmWeaZ_5IRa4I4EOgVwu5oGZ9RSQqQxjRu9P4qY4"

    DATA_WORKSHEET_NAME: str = "Data"
    PAYMENT_DESC_RANGE: str = "B3:B12"

    FINANCES_WORKSHEET_NAME: str = "Gastos"
    AMOUNT_CELL: str = "J2"
    TRANSACTIONS_CELL: str = "B3"


settings = Settings()
collector = Collector()
finances_spreadsheet = FinancesSpreadsheet()


class IOResources:
    APP_ROOT_PATH: Final[Path] = Path("/var", "lib", "vigilant")
    SCREENSHOTS_PATH: Final[str] = "screenshots"

    DATA_DIR: Final[str] = "data_collection"
    DATA_PATH: Final[Path] = APP_ROOT_PATH / DATA_DIR

    OUTPUT_DIR: Final[str] = "output"
    OUTPUT_PATH: Final[Path] = APP_ROOT_PATH / OUTPUT_DIR


class StorageLocation:
    LOCAL: Final[str] = "local"
    GCS: Final[str] = "gcs"
