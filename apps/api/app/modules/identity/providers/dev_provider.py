from app.core.config import settings
from app.modules.identity.auth import build_otp_code, hash_secret
from app.modules.identity.providers.base import OtpDispatchResult, OtpProvider, OtpVerificationResult


class DevOtpProvider(OtpProvider):
    provider_name = "dev"

    def request_code(self, phone: str, channel: str) -> OtpDispatchResult:
        del phone, channel
        code = build_otp_code(settings.otp_length)
        return OtpDispatchResult(
            provider=self.provider_name,
            external_sid=None,
            code_hash=hash_secret(code),
            debug_code=code if settings.expose_otp_in_dev else None,
        )

    def verify_code(
        self,
        *,
        phone: str,
        code: str,
        external_sid: str | None,
        code_hash: str | None,
    ) -> OtpVerificationResult:
        del phone, external_sid
        approved = code_hash is not None and hash_secret(code) == code_hash
        return OtpVerificationResult(
            approved=approved,
            status="approved" if approved else "denied",
        )
