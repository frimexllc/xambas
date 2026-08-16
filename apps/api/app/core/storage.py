"""Almacenamiento de objetos con backend intercambiable.

- `emergent` (por defecto, sin llaves adicionales, usa EMERGENT_LLM_KEY).
- `r2` (Cloudflare R2, S3-compatible vía boto3): listo para producción, solo
  hay que rellenar las variables R2_* en el .env y poner STORAGE_PROVIDER=r2.

La interfaz pública (`init`/`put_object`/`get_object`) es idéntica para ambos,
así que el resto del código no cambia al alternar el proveedor.
"""

import requests

from app.core.config import settings


class _EmergentStorage:
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


class _R2Storage:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name="auto",
            )
        return self._client

    def init(self, force: bool = False) -> str:
        # boto3 no requiere handshake; validamos configuración mínima.
        if not (settings.r2_account_id and settings.r2_bucket):
            raise RuntimeError("R2 no está configurado (faltan R2_ACCOUNT_ID / R2_BUCKET)")
        return "r2"

    def put_object(self, path: str, data: bytes, content_type: str) -> dict:
        self.init()
        self._get_client().put_object(
            Bucket=settings.r2_bucket, Key=path, Body=data, ContentType=content_type
        )
        return {"path": path, "size": len(data)}

    def get_object(self, path: str) -> tuple[bytes, str]:
        self.init()
        obj = self._get_client().get_object(Bucket=settings.r2_bucket, Key=path)
        return obj["Body"].read(), obj.get("ContentType", "application/octet-stream")


def _build_storage():
    if settings.storage_provider == "r2":
        return _R2Storage()
    return _EmergentStorage()


object_storage = _build_storage()
