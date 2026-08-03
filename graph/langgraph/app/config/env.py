from pydantic_settings import BaseSettings
from pydantic import Field

class EnvSettings(BaseSettings):
  llm_key_local: str = Field(..., env="LLM_KEY_LOCAL")
  llm_key_huoshan: str = Field(..., env="LLM_KEY_HUOSHAN")
  llm_key_bailian: str = Field(..., env="LLM_KEY_BAILIAN")

  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"


env = EnvSettings()