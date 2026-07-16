from abc import ABC, abstractmethod

from app.modules.billing.schemas import PaymentProviderConfig


class PaymentGateway(ABC):
    provider_name: str

    @abstractmethod
    def get_config(self) -> PaymentProviderConfig:
        raise NotImplementedError
