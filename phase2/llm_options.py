"""Provider-specific options for stable structured model output."""


def structured_output_options(model):
    """Disable DeepSeek V4 reasoning when the caller requires compact JSON."""
    if str(model or "").lower().startswith("deepseek-v4"):
        return {"extra_body": {"enable_thinking": False}}
    return {}
