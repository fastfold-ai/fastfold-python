from pathlib import Path
from typing import Any, Dict, Optional

from ..http import HTTPClient
from ..models import LibraryFileReference, LibraryItem


class LibraryService:
    def __init__(self, http: HTTPClient):
        self._http = http

    def create_item(
        self,
        *,
        name: str,
        type: str,
        parent_id: Optional[str] = None,
        file_type: Optional[str] = None,
        origin: Optional[str] = None,
        size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        color_hex: Optional[str] = None,
    ) -> LibraryItem:
        payload: Dict[str, Any] = {"name": name, "type": type}
        if parent_id:
            payload["parent_id"] = parent_id
        if file_type:
            payload["fileType"] = file_type
        if origin:
            payload["origin"] = origin
        if size is not None:
            payload["size"] = size
        if metadata is not None:
            payload["metadata"] = metadata
        if color_hex:
            payload["colorHex"] = color_hex
        data = self._http.post("/v1/library/create", json=payload)
        return LibraryItem.from_api(data)

    def get_item(self, item_id: str) -> LibraryItem:
        data = self._http.get(f"/v1/library/{item_id}")
        return LibraryItem.from_api(data)

    def upload_files(self, item_id: str, *file_paths: str) -> LibraryItem:
        if not file_paths:
            raise ValueError("At least one file path is required.")
        handles = []
        files = []
        try:
            for file_path in file_paths:
                path = Path(file_path).expanduser().resolve()
                handle = path.open("rb")
                handles.append(handle)
                files.append(("files", (path.name, handle)))
            data = self._http.post_multipart(f"/v1/library/{item_id}/upload-files", files=files)
            return LibraryItem.from_api(data)
        finally:
            for handle in handles:
                handle.close()

    def upload_file_and_get_ref(
        self,
        *,
        file_path: str,
        file_type: str,
        item_name: str,
        parent_id: Optional[str] = None,
        origin: str = "USER_UPLOAD",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LibraryFileReference:
        path = Path(file_path).expanduser().resolve()
        item = self.create_item(
            name=item_name,
            type="file",
            parent_id=parent_id,
            file_type=file_type,
            origin=origin,
            size=path.stat().st_size,
            metadata=metadata or {},
        )
        uploaded = self.upload_files(item.id, str(path))
        stored_file_name = uploaded.stored_file_name()
        if not stored_file_name:
            raise ValueError(f"Upload response for library item {uploaded.id} did not include a stored file name.")
        return LibraryFileReference(library_item_id=uploaded.id, file_name=stored_file_name)
