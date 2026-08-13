"""Almacenamiento de objetos.

Implementación actual: Emergent Object Storage (sin llaves adicionales, usa
EMERGENT_LLM_KEY). La interfaz es deliberadamente pequeña (init/put/get) para
poder cambiar el backend a Cloudflare R2 (boto3, S3-compatible) más adelante
sin tocar el resto del código: basta con reimplementar estos tres métodos.
"""

import requests

from app.core.config import settings


class ObjectStorage:
    def __init__(self) -> None:
        base = (settings.integration_proxy_url or "").strip() or "https://integrations.emergentagent.com"
        self._storage_url = base.rstrip("/") + "/objstore/api/v1/storage"
        self._storage_key: str | None = None

    def init(self, force: bool = False) -> str:
        if self._storage_key and not force:
            return self._storage_key
        response = requests.post(
            f"{self._storage_url}/init",
            json={"emergent_key": settings.emergent_llm_key},
            timeout=30,
        )
        response.raise_for_status()
        self._storage_key = response.json()["storage_key"]
        return self._storage_key

    def put_object(self, path: str, data: bytes, content_type: str) -> dict:
        key = self.init()
        response = requests.put(
            f"{self._storage_url}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data,
            timeout=120,
        )
        if response.status_code == 404:
            # storage_key inactivo: renovar una vez y reintentar
            key = self.init(force=True)
            response = requests.put(
                f"{self._storage_url}/objects/{path}",
                headers={"X-Storage-Key": key, "Content-Type": content_type},
                data=data,
                timeout=120,
            )
        response.raise_for_status()
        return response.json()

    def get_object(self, path: str) -> tuple[bytes, str]:
        key = self.init()
        response = requests.get(
            f"{self._storage_url}/objects/{path}",
            headers={"X-Storage-Key": key},
            timeout=60,
        )
        response.raise_for_status()
        return response.content, response.headers.get("Content-Type", "application/octet-stream")


object_storage = ObjectStorage()
