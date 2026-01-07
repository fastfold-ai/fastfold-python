from typing import Optional


class FastFoldError(Exception):
    pass


class AuthenticationError(FastFoldError):
    pass


class APIError(FastFoldError):
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional["object"] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class RateLimitError(APIError):
    pass




