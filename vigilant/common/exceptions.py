class VigilantException(Exception):
    """Base exception for any error in Vigilant app"""

    message: str = "Vigilant App Error"

    def __str__(self) -> str:
        return self.message


class DataCollectorException(VigilantException):
    """Base exception for any error in Data Collector process"""

    message: str = "Data Collection Error"


class DriverException(DataCollectorException):
    """Error while navigating through browser"""

    def __init__(self, screenshot_path: str):
        self.message = f"Error encountered while navigating through browser. Check last state screenshot in: {screenshot_path}"


class DownloadTimeout(DataCollectorException):
    """Timeout reached while waiting to download file"""

    def __init__(self, timeout: float):
        self.message = f"Download timeout reached. ({timeout} sec)"


class LoginRejected(DataCollectorException):
    """Error raised when a login form refuses the submitted credentials"""

    def __init__(self, detail: str):
        self.message = f"Login rejected: {detail}"


class LoginBlocked(DataCollectorException):
    """Error raised when the portal cannot serve the login attempt.

    Anti-bot systems answer the submission with a temporary "try later" or
    challenge page instead of the login outcome, without ever rejecting the
    credentials. It is distinct from `LoginRejected` so callers can retry the
    attempt without confusing it with a wrong-credentials refusal.
    """

    def __init__(self, detail: str):
        self.message = f"Login blocked: {detail}"


class FieldValueMismatch(VigilantException):
    """Error raised when a field does not hold the requested value.

    The message names the field only: a value never belongs in a log line or
    in an exception that may be reported elsewhere.
    """

    def __init__(self, selector: str):
        self.message = f"Field {selector} does not hold the expected value"
