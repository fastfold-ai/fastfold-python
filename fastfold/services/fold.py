from typing import Any, Dict, Optional, List

from ..http import HTTPClient
from ..models import Job


class FoldService:
    def __init__(self, http: HTTPClient):
        self._http = http

    def create(
        self,
        model: str,
        name: Optional[str] = None,
        is_public: Optional[bool] = None,
        sequences: Optional[List[Dict[str, Any]]] = None,
        sequence: Optional[str] = None,
        from_id: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """
        Create a folding job.

        Minimal usage (backwards compatible):
            create(model="boltz-2", sequence="...")

        Typed sequences per API:
            create(
                model="boltz-2",
                sequences=[
                    {"proteinChain": {"sequence": "...", "chain_id": "A"}},
                    {"ligandSequence": {"sequence": "ATP", "is_ccd": True, "chain_id": "B"}},
                ],
                is_public=False,
            )
        """
        if sequences is None:
            if not sequence:
                raise ValueError("Either 'sequences' or 'sequence' must be provided.")
            resolved_sequences: List[Dict[str, Any]] = [
                {"proteinChain": {"sequence": sequence}}
            ]
        else:
            resolved_sequences = sequences

        payload: Dict[str, Any] = {"name": name or "FastFold Job", "sequences": resolved_sequences, "params": {"modelName": model}}

        if is_public is not None:
            payload["isPublic"] = is_public

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




