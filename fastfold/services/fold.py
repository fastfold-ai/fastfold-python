from typing import Any, Dict, Optional

from ..http import HTTPClient
from ..models import Job


class FoldService:
    def __init__(self, http: HTTPClient):
        self._http = http

    def create(
        self,
        sequence: str,
        model: str,
        name: Optional[str] = None,
        from_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """
        Create a folding job.

        Minimal usage:
            create(sequence="...", model="boltz-2")
        """
        payload: Dict[str, Any] = {
            "name": name or "FastFold Job",
            "sequences": [
                {
                    "proteinChain": {
                        "sequence": sequence,
                    }
                }
            ],
            "params": {
                "modelName": model,
            },
        }

        if params:
            # Merge/override provided params
            payload["params"].update(params)

        if constraints:
            payload["constraints"] = constraints

        query_params: Dict[str, Any] = {}
        if from_id:
            query_params["from"] = from_id

        data = self._http.post("/v1/jobs", json=payload, params=query_params)
        return Job.from_api(data)


