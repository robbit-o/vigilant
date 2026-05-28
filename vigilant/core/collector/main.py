from typing import Type

from vigilant.core.collector.scraper import (
    BancoChileScraper,
    BancoFalabellaScraper,
    Scraper,
)
from vigilant.common.values import collector


SCRAPER_REGISTRY: dict[str, Type[Scraper]] = {
    "BancoChile": BancoChileScraper,
    "BancoFalabella": BancoFalabellaScraper,
}


def get_enabled_scrapers() -> dict[str, Type[Scraper]]:
    enabled = collector.ENABLED_SCRAPERS
    return {
        name.strip(): SCRAPER_REGISTRY[name.strip()]
        for name in enabled
        if name.strip() in SCRAPER_REGISTRY
    }
