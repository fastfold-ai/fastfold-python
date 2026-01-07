from typing import Any, Dict, Optional

from ..http import HTTPClient
from ..models import JobResults, JobPublicUpdateResponse
from ..errors import APIError
import time


class JobsService:
    def __init__(self, http: HTTPClient):
        self._http = http

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


