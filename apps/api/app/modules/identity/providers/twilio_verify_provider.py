from importlib import import_module

from fastapi import HTTPException, status

from app.core.config import settings
from app.modules.identity.providers.base import OtpDispatchResult, OtpProvider, OtpVerificationResult


class TwilioVerifyProvider(OtpProvider):
    provider_name = "twilio"

    def __init__(self) -> None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_verify_service_sid:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Twilio Verify no esta configurado",
            )

        twilio_module = import_module("twilio.rest")
        client_class = getattr(twilio_module, "Client")
        self._client = client_class(settings.twilio_account_sid, settings.twilio_auth_token)

    def request_code(self, phone: str, channel: str) -> OtpDispatchResult:
        verification = self._client.verify.v2.services(settings.twilio_verify_service_sid).verifications.create(
            to=phone,
            channel=channel,
        )
        return OtpDispatchResult(
            provider=self.provider_name,
            external_sid=verification.sid,
            code_hash=None,
            debug_code=None,
        )

    def verify_code(
        self,
        *,
        phone: str,
        code: str,
        external_sid: str | None,
        code_hash: str | None,
    ) -> OtpVerificationResult:
        del external_sid, code_hash
        check = self._client.verify.v2.services(settings.twilio_verify_service_sid).verification_checks.create(
            to=phone,
            code=code,
        )
        return OtpVerificationResult(
            approved=check.status == "approved",
            status=check.status,
        )
