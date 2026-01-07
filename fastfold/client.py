import os
from typing import Optional

from .errors import AuthenticationError
from .http import HTTPClient
from .services.fold import FoldService
from .services.jobs import JobsService


class Client:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 30.0):
        resolved_api_key = api_key or os.getenv("FASTFOLD_API_KEY")
        if not resolved_api_key:
            raise AuthenticationError(
                "FASTFOLD_API_KEY is not set and no api_key was provided. "
                "Set the environment variable or pass api_key to Client(api_key=...)."
            )

        resolved_base_url = base_url or os.getenv("FASTFOLD_BASE_URL") or "https://api.fastfold.ai"
        self._http = HTTPClient(base_url=resolved_base_url, api_key=resolved_api_key, timeout=timeout)

        # Services
        self.fold = FoldService(self._http)
        self.jobs = JobsService(self._http)




