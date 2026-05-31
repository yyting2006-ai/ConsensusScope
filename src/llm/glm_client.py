from src.llm.openai_compatible import OpenAICompatibleClient


def build_glm_client(**kwargs) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        provider="glm",
        api_key_env="GLM_API_KEY",
        base_url_env="GLM_BASE_URL",
        model_env="GLM_MODEL",
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4-flash",
        **kwargs,
    )
