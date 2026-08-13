from typing import Literal

from pydantic import BaseModel, Field


SenderRole = Literal["client", "provider"]


class ThreadGetOrCreateRequest(BaseModel):
    match_id: str


class ThreadSummary(BaseModel):
    id: str
    match_id: str
    request_id: str
    client_id: str
    provider_user_id: str
    created_at: str
    last_message_at: str | None = None
    contact_unlocked: bool = False


class MessageCreateRequest(BaseModel):
    sender_id: str
    sender_role: SenderRole
    body: str = Field(min_length=1, max_length=2000)


class MessageSummary(BaseModel):
    id: str
    thread_id: str
    sender_id: str
    sender_role: SenderRole
    body: str
    created_at: str
    flagged: bool = False
    flag_reasons: list[str] = Field(default_factory=list)


class MessageListResponse(BaseModel):
    module: str
    thread_id: str
    total: int
    items: list[MessageSummary]


class MessagingStatusResponse(BaseModel):
    module: str
    status: str
    collections: list[str]
