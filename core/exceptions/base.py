class APIError(Exception):
    def __init__(self, error: str, response_data: dict = None):
        self.error = error
        self.response_data = response_data

    @property
    def error_message(self) -> str:
        if self.response_data and "error" in self.response_data:
            return self.response_data["error"]

    def __str__(self):
        return self.error


class SessionRateLimited(Exception):
    """Raised when the session is rate limited"""

    pass


class CaptchaSolvingFailed(Exception):
    """Raised when the captcha solving failed"""

    pass


class ServerError(APIError):
    """Raised when the server returns an error"""

    pass
