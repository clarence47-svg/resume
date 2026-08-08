from langchain_openai import ChatOpenAI

from core.settings import Settings, get_settings


def get_profile_model(settings: Settings | None = None) -> ChatOpenAI:
    resolved = settings or get_settings()
    if not resolved.llm_configured:
        raise RuntimeError("LLM 未配置，请设置 LLM_API_KEY 和 PROFILE_MODEL。")
    return ChatOpenAI(
        api_key=resolved.llm_api_key,
        base_url=resolved.llm_base_url,
        model=resolved.profile_model,
        temperature=0,
        max_retries=2,
    )


def get_match_model(settings: Settings | None = None) -> ChatOpenAI:
    resolved = settings or get_settings()
    if not resolved.llm_configured:
        raise RuntimeError("LLM 未配置，请设置 LLM_API_KEY 和 PROFILE_MODEL。")
    return ChatOpenAI(
        api_key=resolved.llm_api_key,
        base_url=resolved.llm_base_url,
        model=resolved.match_model or resolved.profile_model,
        temperature=0,
        max_retries=2,
    )
