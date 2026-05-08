import json as _json
from typing import Any, Dict, Mapping, Optional

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
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"fastfold-python/{_FASTFOLD_VERSION}",
            }
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        files: Optional[Any] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        request_headers = dict(headers or {})
        if files:
            request_headers["Content-Type"] = None
        resp = self.session.request(
            method.upper(),
            url,
            params=dict(params or {}),
            json=json,
            data=data,
            files=files,
            headers=request_headers or None,
            timeout=self.timeout if timeout is None else timeout,
        )
        return resp

    def get(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        resp = self.request("GET", path, params=params)
        return self._handle_response(resp)

    def post(self, path: str, json: Optional[Any] = None, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        resp = self.request("POST", path, json=json, params=params)
        return self._handle_response(resp)

    def patch(self, path: str, json: Optional[Any] = None, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        resp = self.request("PATCH", path, json=json, params=params)
        return self._handle_response(resp)

    def post_text(
        self,
        path: str,
        text: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        content_type: str = "text/yaml",
    ) -> Dict[str, Any]:
        resp = self.request(
            "POST",
            path,
            params=params,
            data=text.encode("utf-8"),
            headers={"Content-Type": content_type, "Accept": "application/json"},
        )
        return self._handle_response(resp)

    def get_text(self, path: str, params: Optional[Mapping[str, Any]] = None) -> str:
        resp = self.request("GET", path, params=params, headers={"Accept": "text/yaml, text/plain, */*"})
        self._raise_for_status(resp)
        return resp.text

    def post_multipart(
        self,
        path: str,
        *,
        files: Any,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        resp = self.request("POST", path, params=params, files=files, headers=headers)
        return self._handle_response(resp)

    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        if resp.status_code == 401:
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

    @staticmethod
    def _handle_response(resp: requests.Response) -> Dict[str, Any]:
        HTTPClient._raise_for_status(resp)
        try:
            return resp.json()
        except Exception:
            raise APIError("Invalid JSON response from server", status_code=resp.status_code, response=resp)


