from vigilant import logger
from vigilant.common.models import BankSheetConfig
from vigilant.common.storage import clear_resources
from vigilant.core.collector import get_enabled_scrapers
from vigilant.core import SyncService

MAPPING_CONFIG = {
    "BancoChile": BankSheetConfig(
        worksheet="Data",
        amount_cell="E4",
        transactions_cell="D7",
        update_dateime_cell="E2",
    ),
    "BancoFalabella": BankSheetConfig(
        worksheet="Data",
        amount_cell="J4",
        transactions_cell="I7",
        update_dateime_cell="J2",
    ),
}


def main():
    """Process for collecting finances data and load it into a google
    spreadsheet
    """
    logger.info("Collecting transactions data ...")

    clear_resources()

    for bank_id, scraper in get_enabled_scrapers().items():
        SyncService(scraper, MAPPING_CONFIG[bank_id]).sync_bank()

    logger.info("Operation completed successfully")


if __name__ == "__main__":
    main()
