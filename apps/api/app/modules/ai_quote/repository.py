from typing import Any

from bson import ObjectId

from app.core.database import get_database


class AiQuoteRepository:
    def __init__(self) -> None:
        self._db = get_database()

    async def ensure_indexes(self) -> None:
        await self._db.ai_quotes.create_index("client_id")

    async def create_quote(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self._db.ai_quotes.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def get_quote_by_id(self, quote_id: str) -> dict[str, Any] | None:
        return await self._db.ai_quotes.find_one({"_id": ObjectId(quote_id)})

    async def list_quotes(self, client_id: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if client_id is not None:
            query["client_id"] = client_id
        cursor = self._db.ai_quotes.find(query).sort("_id", -1)
        return await cursor.to_list(length=100)
