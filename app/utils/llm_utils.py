def create_llm():
  return {
    "model": "gpt-4o-mini",
    "api_key": "sk-proj-1234567890",
    "api_base": "https://api.openai.com/v1",
    "api_type": "openai",
    "api_version": "2026-07-31",
    "model_kwargs": {
      "temperature": 0.5
    }
  }