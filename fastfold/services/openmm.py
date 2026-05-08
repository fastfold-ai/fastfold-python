from pathlib import Path
from typing import Any, Dict, Optional

from ..models import FrameExtractionResult, LibraryFileReference, WorkflowRun
from .jobs import JobsService
from .library import LibraryService
from .workflows import WorkflowsService


class OpenMMService:
    def __init__(self, jobs: JobsService, workflows: WorkflowsService, library: LibraryService):
        self._jobs = jobs
        self._workflows = workflows
        self._library = library

    @staticmethod
    def _infer_source_ids(results: Any) -> tuple[str, str]:
        job_run_id = str((results.raw or {}).get("jobRunId") or results.raw.get("job_run_id") or "").strip()
        if not job_run_id:
            raise ValueError("Job results did not include a jobRunId.")
        protein_sequences = [sequence for sequence in results.sequences if sequence.type == "protein"]
        source_sequence = protein_sequences[0] if protein_sequences else (results.sequences[0] if results.sequences else None)
        if source_sequence is None:
            raise ValueError("Job results did not include any sequences to use as an OpenMM source.")
        return job_run_id, str(source_sequence.id)

    def submit_from_fold_job(
        self,
        fold_job_id: str,
        *,
        name: Optional[str] = None,
        simulation_name: Optional[str] = None,
        source_job_run_id: Optional[str] = None,
        source_sequence_id: Optional[str] = None,
        preset: str = "single_af_go",
        residue_profile: str = "calvados3",
        temp: float = 293.15,
        ionic: float = 0.15,
        ph: float = 7.5,
        step_size_ns: float = 0.01,
        sim_length_ns: float = 0.2,
        box_length: float = 20,
        is_public: bool = False,
        **workflow_overrides: Any,
    ) -> WorkflowRun:
        if not source_job_run_id or not source_sequence_id:
            results = self._jobs.get_results(fold_job_id)
            inferred_job_run_id, inferred_sequence_id = self._infer_source_ids(results)
            source_job_run_id = source_job_run_id or inferred_job_run_id
            source_sequence_id = source_sequence_id or inferred_sequence_id

        input_payload: Dict[str, Any] = {
            "preset": preset,
            "name": simulation_name or f"openmm_{fold_job_id}",
            "force_field_family": "calvados",
            "residue_profile": residue_profile,
            "temp": float(temp),
            "ionic": float(ionic),
            "pH": float(ph),
            "step_size_ns": float(step_size_ns),
            "sim_length_ns": float(sim_length_ns),
            "box_length": float(box_length),
            "files": {},
            "sourceType": "fold_job",
            "sourceJobId": fold_job_id,
            "sourceJobRunId": source_job_run_id,
            "sourceSequenceId": source_sequence_id,
        }
        if is_public:
            input_payload["isPublic"] = True
        input_payload.update(workflow_overrides)
        return self._workflows.create(
            "calvados_openmm_v1",
            input_payload,
            name=name or f"OpenMM {input_payload['name']}",
        )

    def submit_from_manual_files(
        self,
        *,
        pdb_path: str,
        pae_path: str,
        name: Optional[str] = None,
        simulation_name: Optional[str] = None,
        residue_profile: str = "calvados3",
        temp: float = 293.15,
        ionic: float = 0.15,
        ph: float = 7.5,
        step_size_ns: float = 0.01,
        sim_length_ns: float = 0.2,
        box_length: float = 20,
        is_public: bool = False,
        **workflow_overrides: Any,
    ) -> WorkflowRun:
        pdb = Path(pdb_path).expanduser().resolve()
        pae = Path(pae_path).expanduser().resolve()
        pdb_ref = self._library.upload_file_and_get_ref(
            file_path=str(pdb),
            file_type="protein",
            item_name=f"openmm-structure-{pdb.stem}",
        )
        pae_ref = self._library.upload_file_and_get_ref(
            file_path=str(pae),
            file_type="json",
            item_name=f"openmm-pae-{pae.stem}",
        )
        input_payload: Dict[str, Any] = {
            "preset": "single_af_go",
            "name": simulation_name or f"openmm_{pdb.stem}",
            "force_field_family": "calvados",
            "residue_profile": residue_profile,
            "temp": float(temp),
            "ionic": float(ionic),
            "pH": float(ph),
            "step_size_ns": float(step_size_ns),
            "sim_length_ns": float(sim_length_ns),
            "box_length": float(box_length),
            "files": {
                "pdb": pdb_ref.to_api(),
                "pae": pae_ref.to_api(),
            },
        }
        if is_public:
            input_payload["isPublic"] = True
        input_payload.update(workflow_overrides)
        return self._workflows.create(
            "calvados_openmm_v1",
            input_payload,
            name=name or f"OpenMM {input_payload['name']}",
        )

    def submit_from_workflow(
        self,
        workflow_id: str,
        *,
        name: Optional[str] = None,
        simulation_name: Optional[str] = None,
        is_public: Optional[bool] = None,
        **workflow_overrides: Any,
    ) -> WorkflowRun:
        source = self._workflows.get(workflow_id)
        input_payload = dict(source.input_payload or {})
        if simulation_name:
            input_payload["name"] = simulation_name
        if is_public is not None:
            input_payload["isPublic"] = bool(is_public)
        input_payload.update(workflow_overrides)
        return self._workflows.create(
            "calvados_openmm_v1",
            input_payload,
            name=name or f"OpenMM {(input_payload.get('name') or workflow_id)}",
        )

    def wait_for_completion(
        self,
        workflow_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        results_timeout: float = 900.0,
        public: bool = False,
        log: bool = True,
    ) -> WorkflowRun:
        return self._workflows.wait_for_completion(
            workflow_id,
            poll_interval=poll_interval,
            timeout=timeout,
            results_timeout=results_timeout,
            public=public,
            log=log,
        )

    def extract_frame(
        self,
        workflow_id: str,
        *,
        time_ns: float,
        selection: str = "protein or resname LIG",
        output_filename: str = "extracted_frame.pdb",
        dt_in_ps: float = 0.0,
    ) -> FrameExtractionResult:
        return self._workflows.extract_openmm_frame(
            workflow_id,
            time_ns=time_ns,
            selection=selection,
            output_filename=output_filename,
            dt_in_ps=dt_in_ps,
        )
