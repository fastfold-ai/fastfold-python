import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import yaml

from ..models import JobResults, JobSequence, LibraryFileReference, WorkflowRun
from .jobs import JobsService
from .library import LibraryService
from .workflows import WorkflowsService


def _job_run_id_from_results(results: JobResults) -> str:
    raw = results.raw or {}
    jrid = raw.get("jobRunId") or raw.get("job_run_id")
    if not jrid:
        raise ValueError("Job results did not include jobRunId; pass source_job_run_id explicitly.")
    return str(jrid)


def _pick_sequence(results: JobResults, source_sequence_id: Optional[str]) -> JobSequence:
    if source_sequence_id:
        for seq in results.sequences:
            if str(seq.id) == str(source_sequence_id):
                return seq
        raise ValueError(f"No sequence with id {source_sequence_id!r} in job results.")
    proteins = [s for s in results.sequences if s.type == "protein"]
    if proteins:
        return proteins[0]
    if results.sequences:
        return results.sequences[0]
    raise ValueError("Job results did not include any sequences.")


def _source_user_id_from_cif_url(cif_url: str) -> Optional[str]:
    """If cif_url is a signed artifact URL, path is /{userId}/{jobRunId}/{sequenceId}/{file}."""
    parsed = urlparse(str(cif_url).strip())
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) != 4:
        return None
    if parts[0] == "v1":
        return None
    return parts[0]


def _resolve_source_user_id(cif_url: str, explicit: Optional[str]) -> str:
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    for env_key in ("FASTFOLD_EVOLLA_SOURCE_USER_ID", "FASTFOLD_SOURCE_USER_ID"):
        env_val = (os.getenv(env_key) or "").strip()
        if env_val:
            return env_val
    inferred = _source_user_id_from_cif_url(cif_url)
    if inferred:
        return inferred
    raise ValueError(
        "Could not determine Evolla sourceUserId for this structure URL. "
        "Pass source_user_id=, set FASTFOLD_EVOLLA_SOURCE_USER_ID, "
        "or use a fold CIF URL whose path is /{userId}/{jobRunId}/{sequenceId}/model.cif "
        "(typical signed artifact URL from job results)."
    )


class EvollaService:
    def __init__(self, jobs: JobsService, workflows: WorkflowsService, library: LibraryService):
        self._jobs = jobs
        self._workflows = workflows
        self._library = library

    def submit(
        self,
        workflow_input: Dict[str, Any],
        *,
        name: str = "",
        create_mode: str = "",
    ) -> WorkflowRun:
        return self._workflows.create(
            "evolla_v1",
            workflow_input,
            name=name,
            create_mode=create_mode,
        )

    def submit_from_input_file(
        self,
        path: str,
        *,
        name: str = "",
        create_mode: str = "",
        format: str = "auto",
    ) -> WorkflowRun:
        if str(path) == "-":
            text = sys.stdin.read()
            suffix = ""
        else:
            raw_path = Path(path).expanduser()
            text = raw_path.read_text(encoding="utf-8")
            suffix = raw_path.suffix.lower()
        resolved = format
        if resolved == "auto":
            resolved = "yaml" if str(path) != "-" and suffix in {".yaml", ".yml"} else "json"
        data = yaml.safe_load(text) if resolved == "yaml" else json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("workflow_input file must contain a JSON or YAML object.")
        return self.submit(data, name=name, create_mode=create_mode)

    def submit_from_fold_job(
        self,
        fold_job_id: str,
        question: str,
        *,
        name: Optional[str] = None,
        source_sequence_id: Optional[str] = None,
        source_job_run_id: Optional[str] = None,
        source_user_id: Optional[str] = None,
        is_public: bool = False,
        **workflow_overrides: Any,
    ) -> WorkflowRun:
        q = str(question or "").strip()
        if not q:
            raise ValueError("question is required for Evolla.")
        results = self._jobs.get_results(fold_job_id)
        seq = _pick_sequence(results, source_sequence_id)
        jr_id = source_job_run_id or _job_run_id_from_results(results)
        cif_url = seq.cif_url()
        if not cif_url:
            raise ValueError("Selected sequence has no cif_url yet (job may still be running or structure missing).")
        uid = _resolve_source_user_id(str(cif_url), source_user_id)
        input_payload: Dict[str, Any] = {
            "sourceType": "fold_job",
            "targetSource": "sequence",
            "sourceUserId": uid,
            "sourceJobId": str(fold_job_id),
            "sourceJobRunId": str(jr_id),
            "sourceSequenceId": str(seq.id),
            "cifUrl": str(cif_url),
            "question": q,
        }
        if is_public:
            input_payload["isPublic"] = True
        input_payload.update(workflow_overrides)
        display = (name or "").strip() or f"Evolla {fold_job_id[:8]}"
        return self._workflows.create("evolla_v1", input_payload, name=display)

    def submit_from_local_file(
        self,
        file_path: str,
        question: str,
        *,
        name: Optional[str] = None,
        file_type: str = "protein",
        item_name: Optional[str] = None,
        parent_id: Optional[str] = None,
        model_type: str = "evolla-10b",
        is_public: bool = False,
        **workflow_overrides: Any,
    ) -> WorkflowRun:
        """
        Upload a structure file (.cif, .mmcif, .pdb) to the library and submit Evolla with ``targetSource: upload``,
        matching the web app upload flow.
        """
        q = str(question or "").strip()
        if not q:
            raise ValueError("question is required for Evolla.")
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"No file at {file_path!r}.")
        stem = path.stem
        display_item = (item_name or "").strip() or f"evolla-structure-{stem}"
        ref: LibraryFileReference = self._library.upload_file_and_get_ref(
            file_path=str(path),
            file_type=file_type,
            item_name=display_item,
            parent_id=parent_id,
        )
        input_payload: Dict[str, Any] = {
            "targetSource": "upload",
            "libraryItemId": ref.library_item_id,
            "fileName": ref.file_name,
            "modelType": model_type,
            "question": q,
        }
        if is_public:
            input_payload["isPublic"] = True
        input_payload.update(workflow_overrides)
        display = (name or "").strip() or f"Evolla {stem}"
        return self._workflows.create("evolla_v1", input_payload, name=display)

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
