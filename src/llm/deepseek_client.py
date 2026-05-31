from src.llm.openai_compatible import OpenAICompatibleClient


def build_deepseek_client(**kwargs) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        provider="deepseek",
        api_key_env="DEEPSEEK_API_KEY",
        base_url_env="DEEPSEEK_BASE_URL",
        model_env="DEEPSEEK_MODEL",
        default_base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        **kwargs,
    )
