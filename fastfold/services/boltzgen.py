from pathlib import Path
from typing import Iterable, List, Optional

from ..models import LibraryFileReference, WorkflowRun
from .library import LibraryService
from .workflows import WorkflowsService


class BoltzGenService:
    def __init__(self, workflows: WorkflowsService, library: LibraryService):
        self._workflows = workflows
        self._library = library

    def create_draft(self, *, name: str = "", create_mode: str = "api") -> WorkflowRun:
        return self._workflows.create_graph("boltzgen_v1", name=name, create_mode=create_mode)

    def create_from_workflow_yml(
        self,
        workflow_yml: str,
        *,
        name: str = "",
        create_mode: str = "api",
        execute: bool = False,
    ) -> WorkflowRun:
        return self._workflows.create_from_workflow_yml(
            workflow_name="boltzgen_v1",
            workflow_yml=workflow_yml,
            name=name,
            create_mode=create_mode,
            execute=execute,
        )

    def get_workflow_yml(self, workflow_id: str) -> str:
        return self._workflows.get_workflow_yml(workflow_id)

    def upsert_workflow_yml(self, workflow_id: str, workflow_yml: str) -> dict:
        return self._workflows.set_workflow_yml(workflow_id, workflow_yml)

    def execute(self, workflow_id: str) -> dict:
        return self._workflows.execute(workflow_id)

    def get_logs(self, workflow_id: str) -> dict:
        return self._workflows.get_logs(workflow_id)

    def wait_for_completion(
        self,
        workflow_id: str,
        *,
        poll_interval: float = 10.0,
        timeout: Optional[float] = None,
        results_timeout: float = 0.0,
        log: bool = True,
    ) -> WorkflowRun:
        return self._workflows.wait_for_completion(
            workflow_id,
            poll_interval=poll_interval,
            timeout=timeout,
            results_timeout=results_timeout,
            public=False,
            log=log,
        )

    def upload_input(
        self,
        *,
        file_path: str,
        file_type: Optional[str] = None,
        item_name: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> LibraryFileReference:
        path = Path(file_path).expanduser().resolve()
        inferred_file_type = file_type
        if inferred_file_type is None:
            suffix = path.suffix.lower()
            if suffix in {".yaml", ".yml"}:
                inferred_file_type = "yml"
            elif suffix in {".cif", ".mmcif", ".pdb", ".ent"}:
                inferred_file_type = "protein"
            else:
                inferred_file_type = "other"
        return self._library.upload_file_and_get_ref(
            file_path=str(path),
            file_type=inferred_file_type,
            item_name=item_name or path.stem,
            parent_id=parent_id,
        )

    def upload_inputs(
        self,
        file_paths: Iterable[str],
        *,
        parent_id: Optional[str] = None,
    ) -> List[LibraryFileReference]:
        return [self.upload_input(file_path=file_path, parent_id=parent_id) for file_path in file_paths]

    @staticmethod
    def composer_link(workflow_id: str, *, base_url: str = "https://cloud.fastfold.ai") -> str:
        return f"{base_url.rstrip('/')}/workflow/composer/{workflow_id}"
