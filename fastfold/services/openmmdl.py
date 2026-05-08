from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ..models import FrameExtractionResult, PreparedScriptResult, WorkflowRun
from .library import LibraryService
from .workflows import WorkflowsService


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


class OpenMMDLService:
    def __init__(self, workflows: WorkflowsService, library: LibraryService):
        self._workflows = workflows
        self._library = library

    def prepare_script(self, workflow_input: Dict[str, Any]) -> PreparedScriptResult:
        return self._workflows.prepare_openmmdl_script(workflow_input)

    def submit_from_local_files(
        self,
        *,
        topology_path: str,
        ligand_paths: Optional[Iterable[str]] = None,
        name: Optional[str] = None,
        simulation_name: Optional[str] = None,
        run_analysis: Optional[bool] = None,
        sim_length_ns: Optional[float] = None,
        step_time_ps: Optional[float] = None,
        analysis_cpus: Optional[int] = None,
        failure_retries: Optional[int] = None,
        ligand_selection: Optional[str] = None,
        input_json: Optional[Dict[str, Any]] = None,
        skip_prepare: bool = False,
        draft_script: bool = False,
        is_public: bool = False,
    ) -> WorkflowRun:
        topology = Path(topology_path).expanduser().resolve()
        topology_ref = self._library.upload_file_and_get_ref(
            file_path=str(topology),
            file_type="protein",
            item_name=f"openmmdl-topology-{topology.stem}",
        )
        ligand_refs = []
        for ligand_path in ligand_paths or []:
            ligand = Path(ligand_path).expanduser().resolve()
            ligand_refs.append(
                self._library.upload_file_and_get_ref(
                    file_path=str(ligand),
                    file_type="ligand",
                    item_name=f"openmmdl-ligand-{ligand.stem}",
                ).to_api()
            )

        workflow_input: Dict[str, Any] = {
            "name": simulation_name or f"openmmdl_{topology.stem}",
            "files": {
                "topology": topology_ref.to_api(),
                "ligands": ligand_refs,
            },
        }
        if run_analysis is not None:
            workflow_input["run_analysis"] = bool(run_analysis)
        if sim_length_ns is not None:
            workflow_input["sim_length_ns"] = float(sim_length_ns)
        if step_time_ps is not None:
            workflow_input["step_time_ps"] = float(step_time_ps)
        if analysis_cpus is not None:
            workflow_input["analysis_cpus"] = int(analysis_cpus)
        if failure_retries is not None:
            workflow_input["failure_retries"] = int(failure_retries)
        if ligand_selection is not None:
            workflow_input["ligand_selection"] = str(ligand_selection)
        if is_public:
            workflow_input["isPublic"] = True
        if input_json:
            workflow_input = _deep_merge_dict(workflow_input, input_json)

        if not skip_prepare:
            prepared = self.prepare_script(workflow_input)
            if prepared.workflow_input:
                workflow_input = dict(prepared.workflow_input)

        create_mode = "draft_script" if draft_script else ""
        return self._workflows.create(
            "openmmdl_v1",
            workflow_input,
            name=name or f"OpenMMDL {workflow_input.get('name')}",
            create_mode=create_mode,
        )

    def submit_from_workflow(
        self,
        workflow_id: str,
        *,
        name: Optional[str] = None,
        simulation_name: Optional[str] = None,
        input_json: Optional[Dict[str, Any]] = None,
        prepare: bool = False,
        **workflow_overrides: Any,
    ) -> WorkflowRun:
        source = self._workflows.get(workflow_id)
        workflow_input = dict(source.input_payload or {})
        if simulation_name:
            workflow_input["name"] = simulation_name
        if input_json:
            workflow_input = _deep_merge_dict(workflow_input, input_json)
        workflow_input.update(workflow_overrides)
        if prepare:
            prepared = self.prepare_script(workflow_input)
            if prepared.workflow_input:
                workflow_input = dict(prepared.workflow_input)
        return self._workflows.create(
            "openmmdl_v1",
            workflow_input,
            name=name or f"OpenMMDL {workflow_input.get('name') or workflow_id}",
        )

    def execute_draft(self, workflow_id: str) -> Dict[str, Any]:
        return self._workflows.execute(workflow_id)

    def wait_for_completion(
        self,
        workflow_id: str,
        *,
        poll_interval: float = 5.0,
        timeout: Optional[float] = None,
        results_timeout: float = 1200.0,
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
        return self._workflows.extract_openmmdl_frame(
            workflow_id,
            time_ns=time_ns,
            selection=selection,
            output_filename=output_filename,
            dt_in_ps=dt_in_ps,
        )
