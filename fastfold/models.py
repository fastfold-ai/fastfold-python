from dataclasses import dataclass
from typing import Any, Dict, List, Optional


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



