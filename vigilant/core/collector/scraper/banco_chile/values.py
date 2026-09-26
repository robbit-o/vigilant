from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict


# The login host answers 403 to the login document whenever the user agent is
# not the spoofed one configured in `common.browser`: the session never gets
# past the WAF challenge and the form is never served. Measured with the real
# engine agent, the same document is served with an empty plugin list and no
# `window.chrome` object, and the portal refuses the credentials.
class Secrets(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="CHILE_", extra="ignore"
    )

    USERNAME: str
    PASSWORD: str

    LOGIN_URL: str
    HOME_URL: str
    CREDIT_TRANSACTIONS_URL: str


secrets = Secrets()


class Locators:
    USER_INPUT_ID: Final[str] = "#ppriv_per-login-click-input-rut"
    PASSWORD_INPUT_ID: Final[str] = "#ppriv_per-login-click-input-password"
    LOGIN_BTN_ID: Final[str] = "#ppriv_per-login-click-ingresar-login"

    # Lowercase wording of the message the form shows when it refuses a login
    LOGIN_ERROR_TEXT: Final[str] = "datos ingresados no son correctos"

    PROMOTION_BANNER_CLASS: Final[str] = ".fondo"
    AMOUNT_TEXT_CLASS: Final[str] = ".monto-cuenta"
    DOWNLOAD_TOAST_CLASS: Final[str] = ".snackbar-text"
    NO_TRANSACTIONS_CLASS: Final[str] = ".alert-error"
    LOGOUT_BTN_CLASS: Final[str] = ".button-logout"

    BANNER_CLOSE_BTN_XPATH: Final[str] = (
        '//*[@id="mat-dialog-0"]/fenix-modal-zona-emergente/div/div/div/button'
    )
    DOWNLOAD_GROUP_BTN_XPATH: Final[str] = (
        '//*[@id="mat-tab-content-0-0"]/div/div/fenix-movimientos-no-facturados-tabla/div[1]/div[1]/div[2]/bch-button'
    )
    DOWNLOAD_BTN_XPATH: Final[str] = '//*[@id="cdk-overlay-0"]/div/div/button[1]'


class IOResources:
    TRANSACTIONS_FILENAME: Final[str] = "transactions.xls"
    OUTPUT_FILENAME: Final[str] = "banco_chile.json"
