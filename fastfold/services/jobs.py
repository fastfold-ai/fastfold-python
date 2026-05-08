from typing import Any, Dict, Optional

from ..http import HTTPClient
from ..models import Job, JobResults, JobPublicUpdateResponse
from ..errors import APIError
import time


class JobsService:
    def __init__(self, http: HTTPClient):
        self._http = http

    def create(self, payload: Dict[str, Any], from_id: Optional[str] = None) -> Job:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary matching the JobInput schema.")
        query_params: Dict[str, Any] = {}
        if from_id:
            query_params["from"] = from_id
        data = self._http.post("/v1/jobs", json=payload, params=query_params)
        return Job.from_api(data)

    def create_from_yaml(
        self,
        yaml_text: str,
        *,
        model_name: str,
        name: Optional[str] = None,
        from_id: Optional[str] = None,
        is_public: bool = False,
        run_now: bool = True,
        chat_id: Optional[str] = None,
    ) -> Job:
        params: Dict[str, Any] = {
            "model_name": model_name,
            "is_public": str(bool(is_public)).lower(),
            "run_now": str(bool(run_now)).lower(),
        }
        if name:
            params["name"] = name
        if from_id:
            params["from"] = from_id
        if chat_id:
            params["chat_id"] = chat_id
        data = self._http.post_text("/v1/jobs/from-yaml", yaml_text, params=params)
        return Job.from_api(data)

    def get_results(self, job_id: str) -> JobResults:
        data = self._http.get(f"/v1/jobs/{job_id}/results")
        return JobResults.from_api(data)

    def get_status(self, job_id: str) -> str:
        results = self.get_results(job_id)
        return results.job.status

    def set_public(self, job_id: str, is_public: bool) -> JobPublicUpdateResponse:
        payload: Dict[str, Any] = {"isPublic": bool(is_public)}
        data = self._http.patch(f"/v1/jobs/{job_id}/public", json=payload)
        return JobPublicUpdateResponse.from_api(data)

    def render_yaml(self, payload: Dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary matching the JobInput schema.")
        resp = self._http.request(
            "POST",
            "/v1/jobs/utils/yaml",
            json=payload,
            headers={"Accept": "application/yaml"},
        )
        self._http._raise_for_status(resp)
        return resp.text

    def render_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be a dictionary matching the JobInput schema.")
        return self._http.post("/v1/jobs/utils/json", json=payload)

    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        raise_on_failure: bool = True,
        on_update: Optional[callable] = None,
        log: bool = True,
    ) -> JobResults:
        """
        Poll job status until COMPLETED, FAILED, STOPPED, or timeout.
        Returns JobResults on COMPLETED.
        - poll_interval: seconds between polls
        - timeout: max seconds to wait (None = no timeout)
        - raise_on_failure: raise APIError on FAILED/STOPPED; otherwise return last results
        - on_update: optional callback(status: str) called when status changes
        - log: print status at every poll (useful for scripts/notebooks)
        """
        start_time = time.time()
        last_status: Optional[str] = None
        while True:
            results = self.get_results(job_id)
            status = results.job.status
            if log:
                print(f"[FastFold] job {job_id} status: {status}")
            if status != last_status and on_update:
                on_update(status)
            last_status = status

            if status == "COMPLETED":
                return results
            if status in ("FAILED", "STOPPED"):
                if raise_on_failure:
                    raise APIError(f"Job {status.lower()} while waiting for completion.")
                return results

            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Timed out waiting for job to complete after {timeout} seconds")

            time.sleep(max(0.1, poll_interval))


