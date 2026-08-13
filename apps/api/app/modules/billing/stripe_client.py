"""Wrapper delgado sobre el SDK oficial de Stripe.

Se aisla en un modulo propio (en vez de llamar a `stripe.*` directamente
desde el servicio) para poder sustituir cada funcion por un doble de
prueba y validar la logica de negocio (calculo de montos, maquina de
estados, autorizacion) sin necesidad de red hacia api.stripe.com.
"""

from typing import Any

import stripe

from app.core.config import settings

stripe.api_key = settings.stripe_secret_key


def create_payment_intent(*, amount_cents: int, currency: str, metadata: dict[str, str]) -> Any:
    return stripe.PaymentIntent.create(
        amount=amount_cents,
        currency=currency,
        metadata=metadata,
        automatic_payment_methods={"enabled": True},
    )


def retrieve_payment_intent(payment_intent_id: str) -> Any:
    return stripe.PaymentIntent.retrieve(payment_intent_id)


def create_transfer(
    *, amount_cents: int, currency: str, destination_account_id: str, metadata: dict[str, str]
) -> Any:
    return stripe.Transfer.create(
        amount=amount_cents,
        currency=currency,
        destination=destination_account_id,
        metadata=metadata,
    )


def create_refund(
    *, payment_intent_id: str, amount_cents: int | None = None, reason: str | None = None
) -> Any:
    kwargs: dict[str, Any] = {"payment_intent": payment_intent_id}
    if amount_cents is not None:
        kwargs["amount"] = amount_cents
    if reason is not None:
        kwargs["reason"] = reason
    return stripe.Refund.create(**kwargs)


def create_connected_account(*, email: str, country: str) -> Any:
    return stripe.Account.create(
        type="express",
        country=country,
        email=email,
        capabilities={
            "card_payments": {"requested": True},
            "transfers": {"requested": True},
        },
    )


def retrieve_connected_account(account_id: str) -> Any:
    return stripe.Account.retrieve(account_id)


def create_account_link(*, account_id: str, refresh_url: str, return_url: str) -> Any:
    return stripe.AccountLink.create(
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )


def construct_webhook_event(*, payload: bytes, sig_header: str, webhook_secret: str) -> Any:
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
