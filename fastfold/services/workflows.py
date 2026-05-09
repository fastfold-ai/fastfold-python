import time
from typing import Any, Dict, Optional

from ..errors import APIError
from ..http import HTTPClient
from ..models import (
    FrameExtractionResult,
    PreparedScriptResult,
    WorkflowPublicUpdateResponse,
    WorkflowRun,
    WorkflowStatus,
    WorkflowTaskResults,
)


class WorkflowsService:
    def __init__(self, http: HTTPClient):
        self._http = http

    def create(
        self,
        workflow_name: str,
        workflow_input: Optional[Dict[str, Any]] = None,
        *,
        name: str = "",
        create_mode: str = "",
    ) -> WorkflowRun:
        payload: Dict[str, Any] = {
            "workflow_name": workflow_name,
            "name": name,
            "create_mode": create_mode,
            "workflow_input": workflow_input or {},
        }
        data = self._http.post("/v1/workflows", json=payload)
        return WorkflowRun.from_api(data)

    def get(self, workflow_id: str) -> WorkflowRun:
        data = self._http.get(f"/v1/workflows/{workflow_id}")
        return WorkflowRun.from_api(data)

    def get_public(self, workflow_id: str) -> WorkflowRun:
        data = self._http.get(f"/v1/workflows/public/{workflow_id}")
        return WorkflowRun.from_api(data)

    def status(self, workflow_id: str) -> WorkflowStatus:
        data = self._http.get(f"/v1/workflows/status/{workflow_id}")
        return WorkflowStatus.from_api(data)

    def task_results(self, workflow_id: str) -> WorkflowTaskResults:
        data = self._http.get(f"/v1/workflows/task-results/{workflow_id}")
        return WorkflowTaskResults.from_api(data)

    def execute(self, workflow_id: str) -> Dict[str, Any]:
        return self._http.post("/v1/workflows/execute", json={"workflowId": workflow_id})

    def set_public(self, workflow_id: str, is_public: bool) -> WorkflowPublicUpdateResponse:
        data = self._http.patch(f"/v1/workflows/{workflow_id}/public", json={"isPublic": bool(is_public)})
        return WorkflowPublicUpdateResponse.from_api(data)

    def get_logs(self, workflow_id: str) -> Dict[str, Any]:
        return self._http.get(f"/v1/workflows/logs/{workflow_id}")

    def linked_history(
        self,
        *,
        source_job_id: str,
        source_job_run_id: str,
        source_sequence_id: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "source_job_id": source_job_id,
            "source_job_run_id": source_job_run_id,
            "source_sequence_id": source_sequence_id,
        }
        if limit is not None:
            params["limit"] = limit
        return self._http.get("/v1/workflows/evolla/linked-history", params=params)

    def linked_previews(
        self,
        *,
        source_job_id: str,
        source_job_run_id: str,
        source_sequence_id: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "source_job_id": source_job_id,
            "source_job_run_id": source_job_run_id,
            "source_sequence_id": source_sequence_id,
        }
        if limit is not None:
            params["limit"] = limit
        return self._http.get("/v1/workflows/evolla/linked-previews", params=params)

    def update_evolla_draft_question(self, workflow_id: str, question: str) -> Dict[str, Any]:
        return self._http.patch(f"/v1/workflows/evolla/{workflow_id}/draft-question", json={"question": question})

    def create_graph(self, workflow_name: str, *, name: str = "", create_mode: str = "") -> WorkflowRun:
        payload = {
            "workflow_name": workflow_name,
            "name": name,
            "create_mode": create_mode,
            "workflow_input": {},
        }
        data = self._http.post("/v1/workflows/graph/add", json=payload)
        return WorkflowRun.from_api(data)

    def get_workflow_yml(self, workflow_id: str) -> str:
        return self._http.get_text(f"/v1/workflows/{workflow_id}/workflow.yml")

    def set_workflow_yml(self, workflow_id: str, workflow_yml: str) -> Dict[str, Any]:
        return self._http.post_text(f"/v1/workflows/{workflow_id}/workflow.yml", workflow_yml)

    def create_from_workflow_yml(
        self,
        *,
        workflow_name: str,
        workflow_yml: str,
        name: str = "",
        create_mode: str = "",
        execute: bool = False,
    ) -> WorkflowRun:
        payload = {
            "workflow_name": workflow_name,
            "name": name,
            "create_mode": create_mode,
            "workflow_yml": workflow_yml,
            "execute": bool(execute),
        }
        data = self._http.post("/v1/workflows/graph/from-yaml", json=payload)
        return WorkflowRun.from_api(data)

    def prepare_openmmdl_script(self, workflow_input: Dict[str, Any]) -> PreparedScriptResult:
        data = self._http.post("/v1/workflows/openmmdl/prepare-script", json={"workflow_input": workflow_input})
        return PreparedScriptResult.from_api(data)

    def extract_openmm_frame(
        self,
        workflow_id: str,
        *,
        time_ns: float,
        selection: str = "protein or resname LIG",
        output_filename: str = "extracted_frame.pdb",
        dt_in_ps: float = 0.0,
    ) -> FrameExtractionResult:
        data = self._http.post(
            f"/v1/workflows/openmm/{workflow_id}/extract-frame",
            json={
                "timeNs": float(time_ns),
                "selection": selection,
                "outputFilename": output_filename,
                "dtInPs": float(dt_in_ps),
            },
        )
        return FrameExtractionResult.from_api(data)

    def extract_openmmdl_frame(
        self,
        workflow_id: str,
        *,
        time_ns: float,
        selection: str = "protein or resname LIG",
        output_filename: str = "extracted_frame.pdb",
        dt_in_ps: float = 0.0,
    ) -> FrameExtractionResult:
        data = self._http.post(
            f"/v1/workflows/openmmdl/{workflow_id}/extract-frame",
            json={
                "timeNs": float(time_ns),
                "selection": selection,
                "outputFilename": output_filename,
                "dtInPs": float(dt_in_ps),
            },
        )
        return FrameExtractionResult.from_api(data)

    def wait_for_completion(
        self,
        workflow_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        results_timeout: float = 0.0,
        public: bool = False,
        raise_on_failure: bool = True,
        log: bool = True,
    ) -> WorkflowRun:
        start_time = time.time()
        terminal_seen_at: Optional[float] = None
        while True:
            status = self.status(workflow_id)
            if log:
                print(f"[Fastfold] workflow {workflow_id} status: {status.status}")

            if status.status in {"COMPLETED", "FAILED", "STOPPED"}:
                now = time.time()
                terminal_seen_at = terminal_seen_at or now
                if status.status in {"FAILED", "STOPPED"}:
                    workflow = self.get_public(workflow_id) if public else self.get(workflow_id)
                    if raise_on_failure:
                        raise APIError(f"Workflow {status.status.lower()} while waiting for completion.")
                    return workflow

                workflow = self.get_public(workflow_id) if public else self.get(workflow_id)
                if results_timeout <= 0:
                    return workflow
                if workflow.tasks and any(task.result_raw_json or task.output_library_items for task in workflow.tasks):
                    return workflow
                if (now - terminal_seen_at) >= results_timeout:
                    return workflow

            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Timed out waiting for workflow to complete after {timeout} seconds")

            time.sleep(max(0.1, poll_interval))
