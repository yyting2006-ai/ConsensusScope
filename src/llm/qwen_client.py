from src.llm.openai_compatible import OpenAICompatibleClient


def build_qwen_client(**kwargs) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        provider="qwen",
        api_key_env="QWEN_API_KEY",
        base_url_env="QWEN_BASE_URL",
        model_env="QWEN_MODEL",
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        **kwargs,
    )
