from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import warnings


@dataclass
class Job:
    id: str
    run_id: Optional[str]
    name: Optional[str]
    status: Optional[str]
    sequence_ids: Optional[List[str]]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Job":
        # The API returns jobId, jobRunId, jobName, jobStatus, sequencesIds
        return cls(
            id=data.get("jobId") or data.get("id"),
            run_id=data.get("jobRunId"),
            name=data.get("jobName"),
            status=data.get("jobStatus"),
            sequence_ids=data.get("sequencesIds"),
            raw=data,
        )

@dataclass
class PredictionPayload:
    prediction_status: Optional[str]
    job_run_status: Optional[str]
    msa_status: Optional[str]
    prediction: Optional[bool]
    error: Optional[str]
    mean_plldt: Optional[float]
    execution_time_minutes: Optional[float]
    pdb_url: Optional[str]
    cif_url: Optional[str]
    msa_coverage_plot_url: Optional[str]
    pae_plot_url: Optional[str]
    plddt_plot_url: Optional[str]
    metrics_json_url: Optional[str]
    config_json_url: Optional[str]
    citations_bibtex_url: Optional[str]
    plots_url: Optional[str]
    ptm_score: Optional[float]
    iptm_score: Optional[float]
    max_pae_score: Optional[float]
    seed: Optional[str]
    execution_time_in_minutes: Optional[float]
    affinity_result_raw_json: Optional[Dict[str, Any]]

    @classmethod
    def from_api(cls, data: Optional[Dict[str, Any]]) -> Optional["PredictionPayload"]:
        if data is None:
            return None
        return cls(
            prediction_status=data.get("predictionStatus"),
            job_run_status=data.get("jobRunStatus"),
            msa_status=data.get("msaStatus"),
            prediction=data.get("prediction"),
            error=data.get("error"),
            mean_plldt=data.get("meanPLLDT"),
            execution_time_minutes=data.get("executionTimeInMinutes"),
            pdb_url=data.get("pdb_url"),
            cif_url=data.get("cif_url"),
            msa_coverage_plot_url=data.get("msa_coverage_plot_url"),
            pae_plot_url=data.get("pae_plot_url"),
            plddt_plot_url=data.get("plddt_plot_url"),
            metrics_json_url=data.get("metrics_json_url"),
            config_json_url=data.get("config_json_url"),
            citations_bibtex_url=data.get("citations_bibtex_url"),
            plots_url=data.get("plots_url"),
            ptm_score=data.get("ptm_score"),
            iptm_score=data.get("iptm_score"),
            max_pae_score=data.get("max_pae_score"),
            seed=data.get("seed"),
            execution_time_in_minutes=data.get("execution_time_in_minutes"),
            affinity_result_raw_json=data.get("affinity_result_raw_json"),
        )


class Metrics:
    def __init__(self, payload: PredictionPayload):
        self._payload = payload

    @property
    def mean_PLDDT(self) -> Optional[float]:
        return self._payload.mean_plldt

    # Friendly alias
    @property
    def mean_plddt(self) -> Optional[float]:
        return self._payload.mean_plldt

    @property
    def ptm_score(self) -> Optional[float]:
        return self._payload.ptm_score

    # Common misspelling alias
    @property
    def ptm_scroe(self) -> Optional[float]:
        return self._payload.ptm_score

    @property
    def iptm_score(self) -> Optional[float]:
        return self._payload.iptm_score

    @property
    def max_pae_score(self) -> Optional[float]:
        return self._payload.max_pae_score

    # Boltz-2 (affinity) specific metrics: present only when provided by API
    @property
    def affinity_pred_value(self) -> Optional[float]:
        data = self._payload.affinity_result_raw_json or {}
        return data.get("affinity_pred_value")

    @property
    def affinity_probability_binary(self) -> Optional[float]:
        data = self._payload.affinity_result_raw_json or {}
        return data.get("affinity_probability_binary")

    @property
    def affinity_pred_value1(self) -> Optional[float]:
        data = self._payload.affinity_result_raw_json or {}
        return data.get("affinity_pred_value1")

    @property
    def affinity_probability_binary1(self) -> Optional[float]:
        data = self._payload.affinity_result_raw_json or {}
        return data.get("affinity_probability_binary1")

    @property
    def affinity_pred_value2(self) -> Optional[float]:
        data = self._payload.affinity_result_raw_json or {}
        return data.get("affinity_pred_value2")

    @property
    def affinity_probability_binary2(self) -> Optional[float]:
        data = self._payload.affinity_result_raw_json or {}
        return data.get("affinity_probability_binary2")


@dataclass
class JobSequence:
    id: str
    created_at: str
    updated_at: str
    name: Optional[str]
    sequence: str
    type: str
    prediction_payload: Optional[PredictionPayload]
    job_status: Optional[str] = None

    @classmethod
    def from_api(cls, data: Dict[str, Any], job_status: Optional[str] = None) -> "JobSequence":
        return cls(
            id=data["id"],
            created_at=data["createdAt"],
            updated_at=data["updatedAt"],
            name=data.get("name"),
            sequence=data["sequence"],
            type=data["type"],
            prediction_payload=PredictionPayload.from_api(data.get("predictionPayload")),
            job_status=job_status,
        )

    def cif_url(self) -> Optional[str]:
        if self.job_status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job_status}). CIF URL may be unavailable.")
            return None
        if not self.prediction_payload or not self.prediction_payload.cif_url:
            warnings.warn("[FastFold] No CIF URL available for this sequence.")
            return None
        return self.prediction_payload.cif_url

    def pdb_url(self) -> Optional[str]:
        if self.job_status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job_status}). PDB URL may be unavailable.")
            return None
        if not self.prediction_payload or not self.prediction_payload.pdb_url:
            warnings.warn("[FastFold] No PDB URL available for this sequence.")
            return None
        return self.prediction_payload.pdb_url

    def pae_plot_url(self) -> Optional[str]:
        if self.job_status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job_status}). PAE plot URL may be unavailable.")
            return None
        if not self.prediction_payload or not self.prediction_payload.pae_plot_url:
            warnings.warn("[FastFold] No PAE plot URL available for this sequence.")
            return None
        return self.prediction_payload.pae_plot_url

    def plddt_plot_url(self) -> Optional[str]:
        if self.job_status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job_status}). pLDDT plot URL may be unavailable.")
            return None
        if not self.prediction_payload or not self.prediction_payload.plddt_plot_url:
            warnings.warn("[FastFold] No pLDDT plot URL available for this sequence.")
            return None
        return self.prediction_payload.plddt_plot_url

    def metrics(self) -> "Metrics":
        if self.job_status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job_status}). Metrics may be unavailable.")
        if not self.prediction_payload:
            warnings.warn("[FastFold] No metrics available for this sequence.")
            return Metrics(PredictionPayload.from_api({}))  # all None
        return Metrics(self.prediction_payload)

@dataclass
class JobInfo:
    id: str
    status: str
    name: str
    date: str
    updated_at: str
    is_complex: bool
    is_public: Optional[bool]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "JobInfo":
        return cls(
            id=data["id"],
            status=data["status"],
            name=data["name"],
            date=data["date"],
            updated_at=data["updatedAt"],
            is_complex=data["isComplex"],
            is_public=data.get("isPublic"),
        )


@dataclass
class JobRunResultsSummary:
    count: int
    created_at: Optional[str]
    model_name: Optional[str]
    weight_set: Optional[str]
    method: Optional[str]
    relax_prediction: Optional[bool]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "JobRunResultsSummary":
        return cls(
            count=data["count"],
            created_at=data.get("createdAt"),
            model_name=data.get("modelName"),
            weight_set=data.get("weightSet"),
            method=data.get("method"),
            relax_prediction=data.get("relaxPrediction"),
        )


@dataclass
class JobResults:
    job: JobInfo
    parameters: JobRunResultsSummary
    sequences: List[JobSequence]
    prediction_payload: Optional[PredictionPayload]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "JobResults":
        return cls(
            job=JobInfo.from_api(data["job"]),
            parameters=JobRunResultsSummary.from_api(data["parameters"]),
            sequences=[JobSequence.from_api(s, job_status=data["job"]["status"]) for s in data.get("sequences", [])],
            prediction_payload=PredictionPayload.from_api(data.get("predictionPayload")),
            raw=data,
        )

    def __getitem__(self, index: int) -> "JobSequence":
        return self.sequences[index]

    def __len__(self) -> int:
        return len(self.sequences)

    def cif_url(self) -> Optional[str]:
        if self.job.status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job.status}). CIF URL may be unavailable.")
            return None
        if self.job.is_complex:
            if self.prediction_payload and self.prediction_payload.cif_url:
                return self.prediction_payload.cif_url
            warnings.warn("[FastFold] No CIF URL available for this job.")
            return None
        # Non-complex: if there's exactly one sequence, default to it
        if len(self.sequences) == 1:
            return self.sequences[0].cif_url()
        warnings.warn("[FastFold] Multiple sequences present; use results[i].cif_url() for per-sequence CIF URL.")
        return None

    def pdb_url(self) -> Optional[str]:
        if self.job.status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job.status}). PDB URL may be unavailable.")
            return None
        if self.job.is_complex:
            if self.prediction_payload and self.prediction_payload.pdb_url:
                return self.prediction_payload.pdb_url
            warnings.warn("[FastFold] No PDB URL available for this job.")
            return None
        # Non-complex: if there's exactly one sequence, default to it
        if len(self.sequences) == 1:
            return self.sequences[0].pdb_url()
        warnings.warn("[FastFold] Multiple sequences present; use results[i].pdb_url() for per-sequence PDB URL.")
        return None

    def pae_plot_url(self) -> Optional[str]:
        if self.job.status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job.status}). PAE plot URL may be unavailable.")
            return None
        if self.job.is_complex:
            if self.prediction_payload and self.prediction_payload.pae_plot_url:
                return self.prediction_payload.pae_plot_url
            warnings.warn("[FastFold] No PAE plot URL available for this job.")
            return None
        # Non-complex: if there's exactly one sequence, default to it
        if len(self.sequences) == 1:
            return self.sequences[0].pae_plot_url()
        warnings.warn("[FastFold] Multiple sequences present; use results[i].pae_plot_url() for per-sequence PAE plot URL.")
        return None

    def plddt_plot_url(self) -> Optional[str]:
        if self.job.status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job.status}). pLDDT plot URL may be unavailable.")
            return None
        if self.job.is_complex:
            if self.prediction_payload and self.prediction_payload.plddt_plot_url:
                return self.prediction_payload.plddt_plot_url
            warnings.warn("[FastFold] No pLDDT plot URL available for this job.")
            return None
        # Non-complex: if there's exactly one sequence, default to it
        if len(self.sequences) == 1:
            return self.sequences[0].plddt_plot_url()
        warnings.warn("[FastFold] Multiple sequences present; use results[i].plddt_plot_url() for per-sequence pLDDT plot URL.")
        return None

    def metrics(self) -> "Metrics":
        if self.job.status != "COMPLETED":
            warnings.warn(f"[FastFold] Job is not completed yet (status: {self.job.status}). Metrics may be unavailable.")
        if self.job.is_complex:
            if not self.prediction_payload:
                warnings.warn("[FastFold] No metrics available for this job.")
                return Metrics(PredictionPayload.from_api({}))  # all None
            return Metrics(self.prediction_payload)
        # Non-complex: single sequence convenience
        if len(self.sequences) == 1:
            return self.sequences[0].metrics()
        warnings.warn("[FastFold] Multiple sequences present; use results[i].metrics() for per-sequence metrics.")
        return Metrics(PredictionPayload.from_api({}))  # all None

    def get_viewer_link(self, base_url: Optional[str] = None) -> str:
        """
        Return a link to open the job in the FastFold cloud viewer.
        Default: https://cloud.fastfold.ai/mol/new?from=jobs&job_id=<id>
        """
        host = (base_url or "https://cloud.fastfold.ai").rstrip("/")
        query = urlencode({"from": "jobs", "job_id": self.job.id})
        return f"{host}/mol/new?{query}"


@dataclass
class JobPublicUpdateResponse:
    job_id: str
    is_public: Optional[bool]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "JobPublicUpdateResponse":
        return cls(job_id=data["jobId"], is_public=data.get("isPublic"))


@dataclass
class WorkflowTask:
    task_id: str
    task_type: Optional[str]
    status: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    completion_time_in_seconds: Optional[float]
    output_library_items: Optional[List[Dict[str, Any]]]
    result_raw_json: Optional[Any]
    output: Optional[Dict[str, Any]]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "WorkflowTask":
        return cls(
            task_id=str(data.get("task_id") or data.get("taskId") or ""),
            task_type=data.get("task_type") or data.get("taskType"),
            status=data.get("status"),
            created_at=data.get("created_at") or data.get("createdAt"),
            updated_at=data.get("updated_at") or data.get("updatedAt"),
            completion_time_in_seconds=data.get("completion_time_in_seconds") or data.get("completionTimeInSeconds"),
            output_library_items=data.get("output_library_items") or data.get("outputLibraryItems"),
            result_raw_json=data.get("result_raw_json") or data.get("resultRawJson"),
            output=data.get("output"),
            raw=data,
        )


@dataclass
class WorkflowRun:
    workflow_id: str
    status: Optional[str]
    workflow_type: Optional[str]
    name: Optional[str]
    input_payload: Optional[Dict[str, Any]]
    created_at: Optional[str]
    updated_at: Optional[str]
    tasks_total_count: Optional[int]
    tasks_completed_count: Optional[int]
    tasks_failed_count: Optional[int]
    tasks: List[WorkflowTask]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "WorkflowRun":
        return cls(
            workflow_id=str(data.get("workflow_id") or data.get("workflowId") or ""),
            status=data.get("status"),
            workflow_type=data.get("workflow_type") or data.get("workflowType"),
            name=data.get("name"),
            input_payload=data.get("input_payload") or data.get("inputPayload"),
            created_at=data.get("created_at") or data.get("createdAt"),
            updated_at=data.get("updated_at") or data.get("updatedAt"),
            tasks_total_count=data.get("tasks_total_count") or data.get("tasksTotalCount"),
            tasks_completed_count=data.get("tasks_completed_count") or data.get("tasksCompletedCount"),
            tasks_failed_count=data.get("tasks_failed_count") or data.get("tasksFailedCount"),
            tasks=[WorkflowTask.from_api(item) for item in data.get("tasks", [])],
            raw=data,
        )


@dataclass
class WorkflowStatusTask:
    task_id: str
    task_type: Optional[str]
    status: Optional[str]
    node_id: Optional[str]
    order_index: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    completion_time_in_seconds: Optional[float]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "WorkflowStatusTask":
        return cls(
            task_id=str(data.get("task_id") or data.get("taskId") or ""),
            task_type=data.get("task_type") or data.get("taskType"),
            status=data.get("status"),
            node_id=str(data.get("node_id") or data.get("nodeId") or "") or None,
            order_index=data.get("order_index") or data.get("orderIndex"),
            created_at=data.get("created_at") or data.get("createdAt"),
            updated_at=data.get("updated_at") or data.get("updatedAt"),
            completion_time_in_seconds=data.get("completion_time_in_seconds") or data.get("completionTimeInSeconds"),
            raw=data,
        )


@dataclass
class WorkflowStatus:
    workflow_id: str
    status: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    tasks: List[WorkflowStatusTask]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "WorkflowStatus":
        return cls(
            workflow_id=str(data.get("workflow_id") or data.get("workflowId") or ""),
            status=data.get("status"),
            created_at=data.get("created_at") or data.get("createdAt"),
            updated_at=data.get("updated_at") or data.get("updatedAt"),
            tasks=[WorkflowStatusTask.from_api(item) for item in data.get("tasks", [])],
            raw=data,
        )


@dataclass
class WorkflowTaskResult:
    task_id: str
    task_type: Optional[str]
    parsed_results: Optional[List[Dict[str, Any]]]
    output_library_items: Optional[List[Dict[str, Any]]]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "WorkflowTaskResult":
        return cls(
            task_id=str(data.get("task_id") or data.get("taskId") or ""),
            task_type=data.get("task_type") or data.get("taskType"),
            parsed_results=data.get("parsed_results") or data.get("parsedResults"),
            output_library_items=data.get("output_library_items") or data.get("outputLibraryItems"),
            raw=data,
        )


@dataclass
class WorkflowTaskResults:
    workflow_id: Optional[str]
    status: Optional[str]
    tasks: List[WorkflowTaskResult]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "WorkflowTaskResults":
        task_items = data.get("tasks") or data.get("tasksResults") or data.get("results") or []
        return cls(
            workflow_id=str(data.get("workflow_id") or data.get("workflowId") or "") or None,
            status=data.get("status"),
            tasks=[WorkflowTaskResult.from_api(item) for item in task_items],
            raw=data,
        )


@dataclass
class WorkflowPublicUpdateResponse:
    workflow_id: str
    is_public: bool
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "WorkflowPublicUpdateResponse":
        return cls(
            workflow_id=str(data.get("workflowId") or data.get("workflow_id") or ""),
            is_public=bool(data.get("isPublic")),
            raw=data,
        )


@dataclass
class PreparedScriptResult:
    workflow_input: Optional[Dict[str, Any]]
    generated_script: Optional[str]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "PreparedScriptResult":
        return cls(
            workflow_input=data.get("workflow_input") or data.get("workflowInput"),
            generated_script=data.get("generated_script") or data.get("generatedScript"),
            raw=data,
        )


@dataclass
class FrameExtractionResult:
    workflow_id: str
    task_id: Optional[str]
    pdb_url: Optional[str]
    path: Optional[str]
    frame_index: Optional[int]
    requested_time_ns: Optional[float]
    actual_time_ns: Optional[float]
    atom_count: Optional[int]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "FrameExtractionResult":
        return cls(
            workflow_id=str(data.get("workflowId") or data.get("workflow_id") or ""),
            task_id=str(data.get("taskId") or data.get("task_id") or "") or None,
            pdb_url=data.get("pdbUrl") or data.get("pdb_url"),
            path=data.get("path"),
            frame_index=data.get("frameIndex") or data.get("frame_index"),
            requested_time_ns=data.get("requestedTimeNs") or data.get("requested_time_ns"),
            actual_time_ns=data.get("actualTimeNs") or data.get("actual_time_ns"),
            atom_count=data.get("atomCount") or data.get("atom_count"),
            raw=data,
        )


@dataclass
class LibraryFileReference:
    library_item_id: str
    file_name: str

    def to_api(self) -> Dict[str, str]:
        return {"libraryItemId": self.library_item_id, "fileName": self.file_name}


@dataclass
class LibraryFileMetadata:
    file_name: str
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "LibraryFileMetadata":
        return cls(file_name=str(data.get("file_name") or data.get("fileName") or data.get("name") or ""), raw=data)


@dataclass
class LibraryItem:
    id: str
    name: str
    type: str
    file_type: Optional[str]
    origin: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: Optional[str]
    updated_at: Optional[str]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "LibraryItem":
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            type=str(data.get("type") or ""),
            file_type=data.get("fileType") or data.get("file_type"),
            origin=data.get("origin"),
            metadata=data.get("metadata"),
            created_at=data.get("createdAt") or data.get("created_at"),
            updated_at=data.get("updatedAt") or data.get("updated_at"),
            raw=data,
        )

    def files(self) -> List[LibraryFileMetadata]:
        metadata_files = ((self.metadata or {}).get("files") or [])
        return [LibraryFileMetadata.from_api(item) for item in metadata_files if isinstance(item, dict)]

    def stored_file_name(self) -> Optional[str]:
        files = self.files()
        if files:
            return files[0].file_name
        return None


@dataclass
class SlackReportResult:
    ok: bool
    message: Optional[str]
    needs_slack_setup: bool
    library_item_id: Optional[str]
    raw: Dict[str, Any]

    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "SlackReportResult":
        return cls(
            ok=bool(data.get("ok")),
            message=data.get("message"),
            needs_slack_setup=bool(data.get("needs_slack_setup")),
            library_item_id=str(data.get("library_item_id") or "") or None,
            raw=data,
        )

