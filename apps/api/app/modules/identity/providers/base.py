from dataclasses import dataclass
from typing import Protocol


@dataclass
class OtpDispatchResult:
    provider: str
    external_sid: str | None
    code_hash: str | None
    debug_code: str | None


@dataclass
class OtpVerificationResult:
    approved: bool
    status: str


class OtpProvider(Protocol):
    provider_name: str

    def request_code(self, phone: str, channel: str) -> OtpDispatchResult:
        raise NotImplementedError

    def verify_code(
        self,
        *,
        phone: str,
        code: str,
        external_sid: str | None,
        code_hash: str | None,
    ) -> OtpVerificationResult:
        raise NotImplementedError
