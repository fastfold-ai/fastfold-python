import json as _json
from typing import Any, Dict, Optional

import requests

from .errors import APIError, AuthenticationError, RateLimitError
try:
    # Prefer package-discovered version when installed
    from importlib.metadata import version as _pkg_version  # Python 3.8+: importlib_metadata backport not needed
    _FASTFOLD_VERSION = _pkg_version("fastfold")
except Exception:
    try:
        # Fallback to in-package constant if available
        from . import __version__ as _FASTFOLD_VERSION
    except Exception:
        _FASTFOLD_VERSION = "0"


class HTTPClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"fastfold-python/{_FASTFOLD_VERSION}",
            }
        )

    def post(self, path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.post(url, json=json, params=params, timeout=self.timeout)
        return self._handle_response(resp)

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=self.timeout)
        return self._handle_response(resp)

    def patch(self, path: str, json: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.patch(url, json=json, params=params, timeout=self.timeout)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: requests.Response) -> Dict[str, Any]:
        if resp.status_code == 401:
            # Try to extract error message if provided
            try:
                msg = resp.json().get("message", "Unauthorized")
            except Exception:
                msg = "Unauthorized"
            raise AuthenticationError(msg)

        if resp.status_code == 429:
            try:
                msg = resp.json().get("message", "Too Many Requests")
            except Exception:
                msg = "Too Many Requests"
            raise RateLimitError(msg, status_code=429, response=resp)

        if resp.status_code >= 400:
            try:
                data = resp.json()
                msg = data.get("message") or _json.dumps(data)
            except Exception:
                msg = resp.text or f"HTTP {resp.status_code}"
            raise APIError(msg, status_code=resp.status_code, response=resp)

        try:
            return resp.json()
        except Exception:
            raise APIError("Invalid JSON response from server", status_code=resp.status_code, response=resp)


