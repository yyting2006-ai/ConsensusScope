from src.llm.openai_compatible import OpenAICompatibleClient


def build_kimi_client(**kwargs) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        provider="kimi",
        api_key_env="KIMI_API_KEY",
        base_url_env="KIMI_BASE_URL",
        model_env="KIMI_MODEL",
        default_base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        **kwargs,
    )
