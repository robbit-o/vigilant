from vigilant import logger
from vigilant.core import collector, upload


def main():
    """Process for collecting finances data and load it into a google
    spreadsheet
    """
    collector.collect()
    upload.main()

    logger.info("Operation completed successfully")
