import os
from typing import Optional

from .errors import AuthenticationError
from .http import HTTPClient
from .services.boltzgen import BoltzGenService
from .services.evolla import EvollaService
from .services.fold import FoldService
from .services.jobs import JobsService
from .services.library import LibraryService
from .services.openmm import OpenMMService
from .services.openmmdl import OpenMMDLService
from .services.reports import ReportsService
from .services.workflows import WorkflowsService


class Client:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, timeout: float = 30.0):
        resolved_api_key = api_key or os.getenv("FASTFOLD_API_KEY")
        if not resolved_api_key:
            raise AuthenticationError(
                "FASTFOLD_API_KEY is not set and no api_key was provided. "
                "Set the environment variable or pass api_key to Client(api_key=...)."
            )

        resolved_base_url = base_url or os.getenv("FASTFOLD_BASE_URL") or "https://api.fastfold.ai"
        self._http = HTTPClient(base_url=resolved_base_url, api_key=resolved_api_key, timeout=timeout)

        # Services
        self.fold = FoldService(self._http)
        self.jobs = JobsService(self._http)
        self.workflows = WorkflowsService(self._http)
        self.library = LibraryService(self._http)
        self.openmm = OpenMMService(self.jobs, self.workflows, self.library)
        self.openmmdl = OpenMMDLService(self.workflows, self.library)
        self.evolla = EvollaService(self.jobs, self.workflows, self.library)
        self.boltzgen = BoltzGenService(self.workflows, self.library)
        self.reports = ReportsService(self._http)




