from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    NVIDIA_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    SWIGGY_CLIENT_ID: str = ""
    SWIGGY_CLIENT_SECRET: str = ""
    SWIGGY_MCP_INSTAMART_URL: str = "https://mcp.swiggy.com/im"
    SWIGGY_OAUTH_TOKEN_URL: str = "https://mcp.swiggy.com/oauth/token"
    SWIGGY_OAUTH_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "secret"
    LOG_LEVEL: str = "INFO"
    MOCK_MCP: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
