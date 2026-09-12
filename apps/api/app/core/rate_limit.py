"""Rate limiting de ventana fija respaldado por Mongo.

Se eligió Mongo (en vez de memoria de proceso) porque ya es la fuente de
verdad del resto de la app y el contador queda correcto aunque corran varios
workers de uvicorn — un limitador en memoria no lo estaría.

El identificador de cada "cubeta" (`<key>:<bucket>`) cambia solo con el paso
del tiempo, así que un único `find_one_and_update` con `$inc` es atómico y
evita condiciones de carrera al expirar la ventana (no hace falta borrar nada
a mano; el índice TTL limpia las cubetas viejas).
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from pymongo import ReturnDocument

from app.core.database import get_database


class RateLimiter:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.rate_limit_counters.create_index("expires_at", expireAfterSeconds=0)

    async def hit(self, key: str, *, limit: int, window_minutes: int) -> None:
        """Cuenta un evento bajo `key`; lanza 429 si supera `limit` en la ventana actual."""
        window_seconds = window_minutes * 60
        now = datetime.now(timezone.utc)
        bucket = int(now.timestamp() // window_seconds)
        document = await self._db.rate_limit_counters.find_one_and_update(
            {"_id": f"{key}:{bucket}"},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"expires_at": now + timedelta(seconds=window_seconds * 2)},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if document["count"] > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="demasiados intentos, espera unos minutos antes de volver a intentar",
            )


rate_limiter = RateLimiter()
