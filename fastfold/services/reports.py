from typing import Optional

from ..http import HTTPClient
from ..models import SlackReportResult


class ReportsService:
    def __init__(self, http: HTTPClient):
        self._http = http

    def send_agent_cli_report(
        self,
        markdown: str,
        *,
        report_name: Optional[str] = None,
        save_to_library: bool = True,
    ) -> SlackReportResult:
        payload = {
            "markdown": markdown,
            "report_name": report_name,
            "save_to_library": bool(save_to_library),
        }
        data = self._http.post("/v1/slack/messages/agent-cli-report", json=payload)
        return SlackReportResult.from_api(data)
