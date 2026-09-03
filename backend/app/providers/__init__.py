from app.config import Settings
from app.providers.bailian import BailianProvider
from app.providers.base import ModelProvider
from app.providers.mock import MockProvider


def create_model_provider(settings: Settings) -> ModelProvider:
    if settings.model_provider == "mock":
        return MockProvider()

    if settings.dashscope_api_key is None:
        raise RuntimeError("MODEL_PROVIDER=bailian 时必须设置 DASHSCOPE_API_KEY")

    return BailianProvider(
        api_key=settings.dashscope_api_key.get_secret_value(),
        base_url=settings.bailian_base_url,
        model=settings.bailian_model,
        timeout_seconds=settings.request_timeout_seconds,
    )


__all__ = ["ModelProvider", "create_model_provider"]
